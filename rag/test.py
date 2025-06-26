from src.rag_system import RAGSystem

# Initialize the RAG system
rag = RAGSystem()

# Ask a question
question = "What was the answer to the guardian’s riddle, and how did it help Kai?"
answer = rag.answer_question(question)
print(answer)