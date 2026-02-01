# Text Summarizer

A Python-based text summarization tool that uses GloVe word embeddings and PageRank algorithm to generate extractive summaries of documents.

## Features

- **Extractive Summarization**: Uses sentence similarity and PageRank to identify the most important sentences
- **GloVe Embeddings**: Leverages pre-trained GloVe word vectors for semantic similarity calculation
- **Multiple Input Methods**: Support for single documents, CSV files, or interactive creation
- **GUI Interface**: User-friendly Tkinter-based graphical interface
- **Command Line Interface**: Scriptable command-line tool for automation
- **Batch Processing**: Process multiple documents at once

## Installation

### Prerequisites

- Python 3.8 or higher
- Required packages (automatically installed): pandas, numpy, nltk, scikit-learn, networkx

### Install from PyPI

```bash
pip install text-summarizer-aweebtaku
```

### Install from Source

1. Clone the repository:
```bash
git clone https://github.com/AWeebTaku/Summarizer.git
cd Summarizer
```

2. Install the package:
```bash
pip install -e .
```

### Download GloVe Embeddings

The tool requires GloVe word embeddings. Download the 100d version:

```bash
wget http://nlp.stanford.edu/data/glove.6B.zip
unzip glove.6B.zip
```

Place the `glove.6B.100d.txt` file in the project root or specify the path.

## Usage

### Command Line Interface

```bash
# Summarize a CSV file
text-summarizer-aweebtaku --csv-file data/tennis.csv --article-id 1

# Interactive mode
text-summarizer-aweebtaku
```

### GUI Interface

```bash
python -m text_summarizer.ui
```

### Python API

```python
from text_summarizer import TextSummarizer
import pandas as pd

# Initialize summarizer
summarizer = TextSummarizer(glove_path='glove.6B.100d.txt')

# Load data
df = pd.DataFrame([{'article_id': 1, 'article_text': 'Your text here...'}])

# Run summarization
scored_sentences = summarizer.run_summarization(df)

# Get summary for article ID 1
article_text, summary = summarizer.summarize_article(scored_sentences, 1, df)
print(summary)
```

## Data Format

Input data should be in CSV format with columns:
- `article_id`: Unique identifier for each document
- `article_text`: The full text of the document

Example:
```csv
article_id,article_text
1,"This is the first article. It contains multiple sentences..."
2,"This is the second article. It also has several sentences..."
```

## Algorithm

The summarization process follows these steps:

1. **Sentence Tokenization**: Split documents into individual sentences
2. **Text Cleaning**: Remove punctuation, convert to lowercase, remove stopwords
3. **Sentence Vectorization**: Convert sentences to vectors using GloVe embeddings
4. **Similarity Calculation**: Compute cosine similarity between all sentence pairs
5. **PageRank Scoring**: Apply PageRank algorithm to identify important sentences
6. **Summary Extraction**: Select top-ranked sentences in original order

## Configuration

- `glove_path`: Path to GloVe embeddings file (default: 'glove.6B.100d.txt/glove.6B.100d.txt')
- `num_sentences`: Number of sentences in summary (default: 5)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Citation

If you use this tool in your research, please cite:

```
@software{text_summarizer,
  title = {Text Summarizer},
  author = {Your Name},
  url = {https://github.com/AWeebTaku/Summarizer},
  year = {2024}
}
```