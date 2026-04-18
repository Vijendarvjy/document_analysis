import streamlit as st
import os
import PyPDF2
import docx
from io import BytesIO
import groq

if 'client' not in globals():
    try:
        from google.colab import userdata
        GROQ_API_KEY = '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'
    except ImportError:
        GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

    if not GROQ_API_KEY:
        st.error("GROQ_API_KEY not found. Please set it in Colab secrets or environment variables.")
        st.stop()

    client = groq.Groq(api_key=GROQ_API_KEY)

class DocumentAnalyzerAgent:
    def __init__(self):
        self.client = client

    def analyze_document(self, document_content, document_type):
        try:
            system_prompt = f"""You are an expert document analyzer specializing in {document_type} documents.\n            Provide a comprehensive analysis, including key points, potential risks, opportunities, and a summary.\n            The output should be in markdown format. For '{document_type}' type documents, specifically focus on:\n            - If 'legal': key clauses, compliance issues, contractual obligations.\n            - If 'finance': financial implications, risks, growth opportunities, market trends.\n            - If 'compliance': regulatory adherence, potential penalties, audit readiness.\n            - If 'operations': process inefficiencies, optimization opportunities, operational bottlenecks.\n            - If 'general' or 'other': provide a broad overview of main themes and actionable insights.\n            The analysis should be detailed and insightful, exceeding 500 words.\n            """

            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": document_content,
                    }
                ],
                model="llama3-8b-8192",
                temperature=0.7,
                max_tokens=2000,
            )
            return {"analysis": chat_completion.choices[0].message.content}
        except groq.APITimeoutError as e:
            return {"error": f"Groq API request timed out: {e}"}
        except groq.APIConnectionError as e:
            return {"error": f"Groq API connection error: {e}"}
        except groq.APIStatusError as e:
            return {"error": f"Groq API status error (Code: {e.status_code}): {e.response}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred during analysis: {e}"}

def extract_text_from_pdf(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page_num in range(len(reader.pages)):
        text += reader.pages[page_num].extract_text() or ""
    return text

def extract_text_from_docx(uploaded_file):
    doc = docx.Document(uploaded_file)
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    return "\n".join(text)

st.title("Document Analyzer with Groq")
st.write("Upload or paste documents and get AI-powered analysis.")

if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

tab1, tab2 = st.tabs(["Analyze Document", "Analysis History"])

with tab1:
    st.header("New Analysis")

    uploaded_file = st.file_uploader("Upload a document (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

    document_content = ""
    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            document_content = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            document_content = extract_text_from_docx(uploaded_file)
        elif uploaded_file.type == "text/plain":
            document_content = uploaded_file.read().decode("utf-8")
        st.success(f"Successfully loaded text from {uploaded_file.name}.")

    text_area_content = st.text_area("Or paste your document content here:", height=300, value=document_content)
    if uploaded_file is None and text_area_content:
        document_content = text_area_content

    document_type = st.selectbox(
        "Select Document Type:",
        ("general", "legal", "finance", "compliance", "operations", "other")
    )

    if st.button("Analyze Document"):
        if document_content:
            with st.spinner("Analyzing document..."):
                try:
                    agent = DocumentAnalyzerAgent()
                    analysis_result = agent.analyze_document(document_content, document_type)

                    if "analysis" in analysis_result:
                        st.subheader("Analysis Results:")
                        st.markdown(analysis_result["analysis"])
                        st.session_state.analysis_history.append({
                            "timestamp": st.session_state.get('last_run_timestamp', 'N/A'),
                            "document_type": document_type,
                            "summary": analysis_result["analysis"][:200] + "...",
                            "full_analysis": analysis_result["analysis"]
                        })
                    else:
                        st.error(f"Error during analysis: {analysis_result['error']}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
        else:
            st.warning("Please upload a document or paste some content to analyze.")

with tab2:
    st.header("Analysis History")
    if st.session_state.analysis_history:
        for i, entry in enumerate(reversed(st.session_state.analysis_history)):
            st.subheader(f"Analysis {len(st.session_state.analysis_history) - i} ({entry['document_type']} - {entry.get('timestamp', 'N/A')})")
            st.markdown(entry['summary'])
            with st.expander("View Full Analysis"):
                st.markdown(entry['full_analysis'])
            st.markdown("---")
    else:
        st.info("No analysis history yet. Go to 'Analyze Document' tab to perform an analysis.")
