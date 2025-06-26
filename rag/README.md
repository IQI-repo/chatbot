# Python RAG System with OpenAI

A simple but powerful Retrieval Augmented Generation (RAG) system built with Python and OpenAI. This system helps you build an AI-powered question-answering system that uses your own documents as context.

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-API-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Features

- Document loading and processing
- Text chunking for better context management
- OpenAI embeddings integration
- Similarity-based retrieval system
- Easy-to-use RAG interface
- Configurable chunk sizes and retrieval parameters

## 🚀 Quick Start

1. Clone the repository:
```bash
git clone https://github.com/mazyaryousefinia/python-rag.git
cd python-rag
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

5. Add your documents to `data/documents/`

6. Run a test:
```bash
python test.py
```

## 📁 Project Structure

```
rag-project/
│
├── src/
│   ├── __init__.py
│   ├── document_loader.py
│   ├── text_processor.py
│   ├── embeddings_manager.py
│   ├── retrieval_system.py
│   └── rag_system.py
│
├── data/
│   └── documents/
│
├── requirements.txt
├── README.md
├── test.py
└── .env
```

## 💻 Usage

Here's a simple example of how to use the RAG system:

```python
from src.rag_system import RAGSystem

# Initialize the RAG system
rag = RAGSystem()

# Ask a question
question = "What was the answer to the guardian’s riddle, and how did it help Kai?"
answer = rag.answer_question(question)
print(answer)
```

## 🔧 Configuration

The system can be configured through environment variables:

```env
OPENAI_API_KEY=your_api_key_here
```


## ⚠️ Known Issues

- Large documents may take time to process due to API rate limits
- Memory usage can be high with many documents
- No built-in caching system yet

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for their powerful API
- The open-source community for inspiration and tools

## 📬 Contact

- Create an issue for bug reports or feature requests
- Pull requests are welcome!

## 🔗 Links

- [Blog Post Tutorial](https://dev.to/mazyaryousefinia/building-your-first-rag-system-with-python-and-openai-1326)
- [OpenAI Documentation](https://platform.openai.com/docs/api-reference)
- [Python Documentation](https://docs.python.org/3/)

---
Made with ❤️ by [Mazyar]
