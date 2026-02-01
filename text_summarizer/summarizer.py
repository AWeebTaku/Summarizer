import pandas as pd
import numpy as np
import nltk
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx

# Download necessary NLTK data
# nltk.download('punkt_tab')
# nltk.download('stopwords')

class TextSummarizer:
    """A class for summarizing text documents using GloVe embeddings and PageRank."""

    def __init__(self, glove_path: Optional[str] = None, num_sentences: int = 5):
        self.num_sentences = num_sentences
        self.word_embeddings: Dict[str, np.ndarray] = {}
        self.stop_words: set = set(stopwords.words('english'))

        # Set default GloVe path
        if glove_path is None:
            glove_path = self._get_default_glove_path()

        self.glove_path = glove_path
        self._load_embeddings()

    def _get_default_glove_path(self):
        """Get the default path for GloVe embeddings."""
        # Use user's home directory for data
        home_dir = Path.home()
        glove_dir = home_dir / '.text_summarizer'
        glove_dir.mkdir(exist_ok=True)
        return glove_dir / 'glove.6B.100d.txt'

    def _download_glove_embeddings(self):
        """Download GloVe embeddings if not present with improved error handling."""
        import requests

        print("GloVe embeddings not found. Downloading from Stanford NLP...")

        # Create directory if it doesn't exist
        glove_file = Path(self.glove_path)
        glove_file.parent.mkdir(exist_ok=True)

        # Download the zip file
        url = "https://nlp.stanford.edu/data/glove.6B.zip"
        zip_path = glove_file.parent / "glove.6B.zip"

        headers = {
            'User-Agent': 'TextSummarizer/1.1.0 (https://github.com/AWeebTaku/Summarizer)',
        }

        try:
            print("Downloading GloVe embeddings (862 MB)...")
            with requests.get(url, headers=headers, stream=True, timeout=30) as response:
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                print(".1f", end='', flush=True)

            print("\nDownload complete. Extracting...")

            # Extract the specific file we need
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extract('glove.6B.100d.txt', glove_file.parent)

            # Verify extraction
            if not glove_file.exists():
                raise FileNotFoundError("Failed to extract GloVe file from zip")

            # Clean up zip file
            zip_path.unlink()

            print(f"GloVe embeddings extracted to {self.glove_path}")

        except requests.exceptions.RequestException as e:
            print(f"Network error during download: {e}")
            raise Exception(f"Failed to download GloVe embeddings: {e}")
        except zipfile.BadZipFile as e:
            print(f"Invalid zip file downloaded: {e}")
            if zip_path.exists():
                zip_path.unlink()
            raise Exception("Downloaded file is not a valid zip archive")
        except Exception as e:
            print(f"Unexpected error during download: {e}")
            if zip_path.exists():
                zip_path.unlink()
            raise

    def _load_embeddings(self):
        """Load GloVe word embeddings from file with optimized memory usage."""
        if not os.path.exists(self.glove_path):
            self._download_glove_embeddings()

        try:
            print(f"Loading GloVe embeddings from {self.glove_path}...")
            word_count = 0

            with open(self.glove_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        values = line.split()
                        if len(values) < 101:  # word + 100 dimensions
                            continue

                        word = values[0]
                        coefs = np.asarray(values[1:101], dtype='float32')  # Only take first 100 dims
                        self.word_embeddings[word] = coefs
                        word_count += 1

                        # Progress update every 50k words
                        if word_count % 50000 == 0:
                            print(f"Loaded {word_count} words...")

                    except (ValueError, IndexError) as e:
                        # Skip malformed lines
                        continue

            print(f"Successfully loaded {len(self.word_embeddings)} word embeddings.")

            if len(self.word_embeddings) == 0:
                raise ValueError("No valid embeddings found in GloVe file")

        except FileNotFoundError:
            raise FileNotFoundError(f"GloVe file not found at {self.glove_path}")
        except Exception as e:
            raise Exception(f"Error loading GloVe embeddings: {e}")

    def preprocess_sentences(self, df: pd.DataFrame) -> List[Dict]:
        """Tokenize articles into sentences and store metadata."""
        all_sentences_data = []
        sentence_counter_global = 0
        for _, article_row in df.iterrows():
            article_id = article_row['article_id']
            article_text = article_row['article_text']
            article_sentences = sent_tokenize(article_text)
            for sent_idx, sentence_text in enumerate(article_sentences):
                all_sentences_data.append({
                    'global_sentence_idx': sentence_counter_global,
                    'article_id': article_id,
                    'sentence_text': sentence_text,
                    'original_article_sentence_idx': sent_idx
                })
                sentence_counter_global += 1
        return all_sentences_data

    def clean_sentences(self, sentences):
        """Clean sentences: remove non-alphabetic, lowercase, remove stopwords."""
        if not sentences:
            return []

        # Use pandas for efficient string operations
        clean_sentences = pd.Series(sentences).str.replace(r"[^a-zA-Z\s]", " ", regex=True)
        clean_sentences = clean_sentences.str.lower()
        clean_sentences = clean_sentences.apply(self._remove_stopwords)
        return clean_sentences.tolist()

    def _remove_stopwords(self, sentence):
        """Remove stopwords from a sentence string."""
        if not isinstance(sentence, str):
            return ""
        words = sentence.split()
        filtered_words = [word for word in words if word not in self.stop_words]
        return " ".join(filtered_words)

    def compute_sentence_vectors(self, clean_sentences):
        """Compute sentence vectors using GloVe embeddings with vectorized operations."""
        if not clean_sentences:
            return []

        sentence_vectors = []
        for sentence in clean_sentences:
            words = sentence.split()
            if words:
                # Get embeddings for all words in sentence
                vectors = []
                for word in words:
                    embedding = self.word_embeddings.get(word, np.zeros(100, dtype=np.float32))
                    vectors.append(embedding)

                if vectors:
                    # Use mean of word vectors
                    v = np.mean(vectors, axis=0)
                else:
                    v = np.zeros(100, dtype=np.float32)
            else:
                v = np.zeros(100, dtype=np.float32)
            sentence_vectors.append(v)

        return sentence_vectors

    def compute_similarity_matrix(self, sentence_vectors):
        """Compute cosine similarity matrix using vectorized operations."""
        if not sentence_vectors:
            return np.array([])

        # Convert to numpy array for vectorized operations
        vectors = np.array(sentence_vectors)
        n = len(vectors)

        # Normalize vectors for faster cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized_vectors = vectors / norms

        # Compute cosine similarity matrix using matrix multiplication
        sim_mat = np.dot(normalized_vectors, normalized_vectors.T)

        # Ensure diagonal is zero (no self-similarity)
        np.fill_diagonal(sim_mat, 0)

        return sim_mat

    def rank_sentences(self, sim_mat):
        """Rank sentences using PageRank with optimized parameters."""
        if sim_mat.size == 0:
            return {}

        try:
            # Create graph from similarity matrix
            nx_graph = nx.from_numpy_array(sim_mat)

            # Use optimized PageRank parameters
            scores = nx.pagerank(
                nx_graph,
                alpha=0.85,  # Damping factor
                max_iter=100,
                tol=1e-6
            )

            return scores
        except Exception as e:
            print(f"Warning: PageRank failed, using uniform scores: {e}")
            # Fallback: return uniform scores
            n = sim_mat.shape[0]
            return {i: 1.0/n for i in range(n)}

    def summarize_article(self, scored_sentences, article_id, df):
        """Generate summary for a specific article."""
        article_sentences = [s for s in scored_sentences if s['article_id'] == article_id]
        if not article_sentences:
            return None, None

        article_sentences.sort(key=lambda x: x['score'], reverse=True)
        top_sentences = article_sentences[:self.num_sentences]
        top_sentences.sort(key=lambda x: x['original_article_sentence_idx'])
        summary = " ".join([s['sentence_text'] for s in top_sentences])

        article_row = df[df['article_id'] == article_id]
        if not article_row.empty:
            article_text = article_row['article_text'].iloc[0]
            return article_text, summary
        return None, None

    def summarize_all_articles(self, scored_sentences, df):
        """Generate summaries for all articles."""
        summaries = {}
        for _, article_row in df.iterrows():
            article_id = article_row['article_id']
            article_text, summary = self.summarize_article(scored_sentences, article_id, df)
            if article_text and summary:
                summaries[article_id] = {'article': article_text, 'summary': summary}
        return summaries

    def run_summarization(self, df):
        """Run the full summarization pipeline."""
        sentences_data = self.preprocess_sentences(df)
        sentences = [s['sentence_text'] for s in sentences_data]
        clean_sentences = self.clean_sentences(sentences)
        sentence_vectors = self.compute_sentence_vectors(clean_sentences)
        sim_mat = self.compute_similarity_matrix(sentence_vectors)
        scores = self.rank_sentences(sim_mat)

        for i, sentence_data in enumerate(sentences_data):
            sentence_data['score'] = scores[i]

        return sentences_data

    def summarize_text(self, text: str, num_sentences: Optional[int] = None) -> str:
        """
        Summarize a single text document.

        Args:
            text (str): The text to summarize
            num_sentences (int, optional): Number of sentences in summary. Defaults to self.num_sentences.

        Returns:
            str: The summarized text
        """
        if not text or not text.strip():
            return ""

        if num_sentences is None:
            num_sentences = self.num_sentences

        # Create a temporary DataFrame
        df = pd.DataFrame([{'article_id': 1, 'article_text': text}])

        # Run summarization pipeline
        scored_sentences = self.run_summarization(df)

        # Get summary
        _, summary = self.summarize_article(scored_sentences, 1, df)

        return summary if summary else text