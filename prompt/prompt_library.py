from langchain_core.prompts import ChatPromptTemplate
from enum import Enum

# Prompt for document analysis
document_analysis_prompt = ChatPromptTemplate.from_template("""
You are a highly capable assistant trained to analyze and summarize documents.
Return ONLY valid JSON matching the exact schema below
                                          
{format_instructions}

Analyze this document:
{document_text}

Remember: Output must be valid JSON only, no additional commentary.
""")

# Prompt for document comparison
document_comparison_prompt = ChatPromptTemplate.from_template("""
You are a document comparison assistant. 

You will receive two versions of a PDF document (V1 and V2). Each is split page by page.

Your tasks:
1. Compare the text of each page in V1 with the text of corresponding page in V2 **sentence by sentence**.
2. If the page content is identical, mark as "NO CHANGE".
3. Report all additions, deletions, or modifications of the sentences with a short summary with versions of the pdf.
Always compare V1 vs V2.
4. Do not compare the text within the same document version. Do not report any idnetical sentence summary.
5. Always output results in strict JSON that follows the given schema.

Version 1 (V1):
{doc_v1}

Version 2 (V2):
{doc_v2}

Your response must be a JSON array following this schema:

{format_instruction}
""")

# Prompt for contextualize question
contextualize_question_prompt = ChatPromptTemplate.from_template("""
""")

# Prompt for context qa
context_qa_prompt = ChatPromptTemplate.from_template("""
""")

PROMPT_REGISTRY = {
    "document_analysis"         :   document_analysis_prompt,
    "document_comparison"       :   document_comparison_prompt,
    "contextualize_question"    :   contextualize_question_prompt,
    "context_qa"                :   context_qa_prompt,
}