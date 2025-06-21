import streamlit as st
import asyncio
import os
import tempfile
import json
import nest_asyncio
from typing import Optional, List, Dict

nest_asyncio.apply()

# Import core backend functions and agent classes, not globally initialized instances
from backend_service import analyze_document_pipeline_core, run_rag_query_core, setup_dummy_documents, get_llm_model, get_redis_cache
from agents.rag_agent import RAGAgent # Import the RAGAgent CLASS
from models.document_models import DocumentAnalysisResult, RAGResponse, Node, Edge, ComplianceFinding, Party, DateClause, MonetaryValue, DefinedTerm

st.set_page_config(layout="wide", page_title="Legal AI Agent")

# Initializing session state variables
if 'analyzed_document' not in st.session_state:
    st.session_state.analyzed_document = None
if 'rag_history' not in st.session_state:
    st.session_state.rag_history = []
if 'last_analyzed_file_name' not in st.session_state:
    st.session_state.last_analyzed_file_name = None
if 'llm_model' not in st.session_state: # Cache LLM model
    st.session_state.llm_model = None
if 'redis_cache' not in st.session_state: # Cache Redis cache
    st.session_state.redis_cache = None
if 'rag_agent_instance' not in st.session_state: # Cache RAG agent instance
    st.session_state.rag_agent_instance = None


# Run backend setup and initialize persistent resources once
@st.cache_resource
def initialize_app_resources():
    # Setup dummy documents
    asyncio.run(setup_dummy_documents())
    
    # Get singleton instances of LLM model and Redis cache from backend_service
    llm = get_llm_model()
    cache = get_redis_cache()
    
    rag_agent = RAGAgent(model=llm, cache=cache)
    
    return llm, cache, rag_agent

# Call the setup function to get resources
llm_model, redis_cache, rag_agent_instance = initialize_app_resources()

# Store the LLM model and Redis cache in session state
if st.session_state.rag_agent_instance is None:
    st.session_state.rag_agent_instance = rag_agent_instance


st.title("⚖️ Legal AI Agent: Document Analysis & RAG")
st.markdown("Upload a legal document, analyze its content, identify compliance risks, and ask questions.")

# --- File Upload Section ---
st.header("1. Upload and Analyze Document")
uploaded_file = st.file_uploader("Choose a DOCX, PDF, or TXT file", type=["docx", "pdf", "txt"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        file_path = tmp_file.name

    st.info(f"Analyzing '{uploaded_file.name}'...")

    try:
        with st.spinner("Processing document... This may take a moment."):
            analysis_result = asyncio.run(analyze_document_pipeline_core(
                file_path, 
                llm_model, 
                redis_cache, 
                st.session_state.rag_agent_instance
            ))
        
        if analysis_result:
            st.session_state.analyzed_document = analysis_result
            st.session_state.last_analyzed_file_name = uploaded_file.name
            st.session_state.rag_history = [] # Clear RAG history for new document
            st.success(f"Successfully analyzed '{uploaded_file.name}'!")
        else:
            st.error(f"Failed to analyze '{uploaded_file.name}'. Check console for errors.")

    except Exception as e:
        st.error(f"An unexpected error occurred during analysis: {e}")
    finally:
        os.unlink(file_path)

# --- Display Analysis Results ---
if st.session_state.analyzed_document:
    st.header(f"2. Analysis Results for '{st.session_state.last_analyzed_file_name}'")
    analysis_result = st.session_state.analyzed_document

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Summary", "Parties & Dates", "Monetary & Terms", "Clauses", "Knowledge Graph"])

    with tab1:
        st.subheader("Document Metadata")
        st.json(analysis_result.metadata.model_dump())
        st.subheader("Analysis Summary")
        st.markdown(analysis_result.analysis_summary)
        
        st.subheader("Compliance Findings")
        if analysis_result.compliance_findings:
            for i, finding in enumerate(analysis_result.compliance_findings):
                st.markdown(f"**Rule ID:** {finding.rule_id} ({finding.rule_description})")
                status_emoji = "✅" if finding.is_compliant else "❌"
                st.markdown(f"**Status:** {status_emoji} {'COMPLIANT' if finding.is_compliant else 'NON-COMPLIANT'}")
                st.markdown(f"**Severity:** {finding.severity}")
                if finding.finding_details:
                    st.markdown(f"**Details:** {finding.finding_details}")
                if finding.relevant_text_snippets:
                    with st.expander(f"Relevant Snippets for {finding.rule_id}"):
                        for snippet in finding.relevant_text_snippets:
                            st.code(snippet)
                if finding.recommendation:
                    st.markdown(f"**Recommendation:** {finding.recommendation}")
                st.markdown("---")
        else:
            st.info("No compliance findings to display.")

    with tab2:
        st.subheader("Extracted Parties")
        if analysis_result.extracted_parties:
            for party in analysis_result.extracted_parties:
                st.json(party.model_dump())
        else:
            st.info("No parties extracted.")

        st.subheader("Extracted Dates")
        if analysis_result.extracted_dates:
            for date_item in analysis_result.extracted_dates:
                st.json(date_item.model_dump())
        else:
            st.info("No dates extracted.")

    with tab3:
        st.subheader("Extracted Monetary Values")
        if analysis_result.extracted_monetary_values:
            for mv in analysis_result.extracted_monetary_values:
                st.json(mv.model_dump())
        else:
            st.info("No monetary values extracted.")
        
        st.subheader("Extracted Defined Terms")
        if analysis_result.extracted_defined_terms:
            for dt in analysis_result.extracted_defined_terms:
                st.json(dt.model_dump())
        else:
            st.info("No defined terms extracted.")

    with tab4:
        st.subheader("Extracted Clauses")
        if analysis_result.extracted_clauses_summary:
            for clause_type, clauses in analysis_result.extracted_clauses_summary.items():
                st.markdown(f"**{clause_type.replace('Clause', ' Clause')} ({len(clauses)} found):**")
                for clause in clauses:
                    st.json(clause)
                st.markdown("---")
        else:
            st.info("No specific clauses extracted.")

    with tab5:
        st.subheader("Knowledge Graph Nodes")
        if analysis_result.knowledge_graph and analysis_result.knowledge_graph.nodes:
            for node in analysis_result.knowledge_graph.nodes:
                st.json(node.model_dump())
        else:
            st.info("No Knowledge Graph nodes generated.")
        
        st.subheader("Knowledge Graph Edges")
        if analysis_result.knowledge_graph and analysis_result.knowledge_graph.edges:
            for edge in analysis_result.knowledge_graph.edges:
                st.json(edge.model_dump())
        else:
            st.info("No Knowledge Graph edges generated.")


    # --- Interactive RAG Query Section  ---
    st.header("3. Ask Questions (RAG)")

    for chat_message in st.session_state.rag_history:
        with st.chat_message(chat_message["role"]):
            st.markdown(chat_message["content"])
            if chat_message.get("relevant_snippets"):
                with st.expander("Relevant Snippets"):
                    for snippet in chat_message["relevant_snippets"]:
                        st.code(snippet)
            if chat_message.get("source_nodes"):
                with st.expander("Source KG Nodes (IDs)"):
                    for node_id in chat_message["source_nodes"]:
                        st.write(node_id)


    # Accept user input
    if prompt := st.chat_input("Enter your question about the document..."):
        st.session_state.rag_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.spinner("Getting answer..."):
            if st.session_state.analyzed_document:
                rag_response: RAGResponse = asyncio.run(run_rag_query_core(prompt, st.session_state.rag_agent_instance))
                
                # Add AI response to chat history
                ai_message_content = f"AI Answer (Confidence: {rag_response.confidence}):\n{rag_response.answer}"
                st.session_state.rag_history.append({
                    "role": "assistant", 
                    "content": ai_message_content,
                    "relevant_snippets": rag_response.relevant_snippets,
                    "source_nodes": rag_response.source_nodes
                })
                
                # Display AI response in chat message container
                with st.chat_message("assistant"):
                    st.markdown(ai_message_content)
                    if rag_response.relevant_snippets:
                        with st.expander("Relevant Snippets"):
                            for snippet in rag_response.relevant_snippets:
                                st.code(snippet)
                    if rag_response.source_nodes:
                        with st.expander("Source KG Nodes (IDs)"):
                            for node_id in rag_response.source_nodes:
                                st.write(node_id)
            else:
                warning_message = "Please upload and analyze a document first to ask questions."
                st.session_state.rag_history.append({"role": "assistant", "content": warning_message})
                with st.chat_message("assistant"):
                    st.warning(warning_message)

else:
    st.info("Upload a document above to start the analysis.")

