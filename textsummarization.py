import pandas as pd
import numpy as np
import nltk
import os
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx

# Download necessary NLTK data
# nltk.download('punkt_tab')
# nltk.download('stopwords')

class TextSummarizer:
    """A class for summarizing text documents using GloVe embeddings and PageRank."""

    def __init__(self, glove_path='glove.6B.100d.txt/glove.6B.100d.txt', num_sentences=5):
        self.glove_path = glove_path
        self.num_sentences = num_sentences
        self.word_embeddings = {}
        self.stop_words = set(stopwords.words('english'))
        self._load_embeddings()

    def _load_embeddings(self):
        """Load GloVe word embeddings from file."""
        try:
            with open(self.glove_path, 'r', encoding='utf-8') as f:
                for line in f:
                    values = line.split()
                    word = values[0]
                    coefs = np.asarray(values[1:], dtype='float32')
                    self.word_embeddings[word] = coefs
        except FileNotFoundError:
            raise FileNotFoundError(f"GloVe file not found at {self.glove_path}")

    def load_data(self):
        """Load data interactively."""
        while True:
            choice = input("Enter 'P' to paste a single article,\n'U' to upload a CSV with multiple articles,\n'C' to create a new CSV with multiple articles: ").upper()
            df = pd.DataFrame()
            save_csv = True

            if choice == 'P':
                article_text = input("Paste your article text here:\n")
                df = pd.DataFrame([{'article_id': 1, 'article_text': article_text}])
                print('DataFrame created from single article.')
                save_csv = False
                break
            elif choice == 'U':
                print("You chose to load an existing CSV file. It should contain 'article_id' and 'article_text' columns.")
                save_csv = False
                while True:
                    file_name = input("Enter the name of the CSV file (e.g., 'tennis.csv') or type 'cancel' to go back: ").strip()
                    if file_name.lower() == 'cancel':
                        break
                    if os.path.exists(file_name) and file_name.lower().endswith('.csv'):
                        try:
                            df = pd.read_csv(file_name)
                            print(f'CSV file "{file_name}" loaded successfully.')
                            break
                        except Exception as e:
                            print(f"Error reading file '{file_name}': {e}")
                    else:
                        print(f"File '{file_name}' not found or is not a CSV. Please try again.")
                if not df.empty:
                    break
            elif choice == 'C':
                print("You've chosen to create a CSV with multiple articles. Enter 'done' for article ID when finished.")
                articles_data = []
                article_counter = 1
                while True:
                    article_id_input = input(f"Enter article ID for article {article_counter} (or 'done' to finish): ").strip()
                    if article_id_input.lower() == 'done':
                        break
                    try:
                        article_id = int(article_id_input)
                    except ValueError:
                        print("Invalid Article ID. Please enter a number or 'done'.")
                        continue
                    article_text = input("Enter article text:\n").strip()
                    if not article_text:
                        print("Article text cannot be empty. Please try again.")
                        continue
                    articles_data.append({'article_id': article_id, 'article_text': article_text})
                    article_counter += 1
                if articles_data:
                    df = pd.DataFrame(articles_data)
                    print('DataFrame created from multiple articles.')
                    break
                else:
                    print("No articles were entered. Please try again or choose another option.")
            else:
                print("Invalid choice. Please enter 'P', 'U', or 'C'.")

        if not df.empty and save_csv:
            df.to_csv('article.csv', index=False)
            print('CSV file "article.csv" created/updated successfully.')
        elif df.empty:
            print("No DataFrame was created.")
        return df

    def preprocess_sentences(self, df):
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
        clean_sentences = pd.Series(sentences).str.replace(r"[^a-zA-Z\s]", " ", regex=True)
        clean_sentences = clean_sentences.str.lower()
        clean_sentences = clean_sentences.apply(lambda s: self._remove_stopwords(s.split()))
        return clean_sentences.tolist()

    def _remove_stopwords(self, sen):
        """Remove stopwords from a list of words."""
        return " ".join([word for word in sen if word not in self.stop_words])

    def compute_sentence_vectors(self, clean_sentences):
        """Compute sentence vectors using GloVe embeddings."""
        sentence_vectors = []
        for sentence in clean_sentences:
            words = sentence.split()
            if words:
                vectors = [self.word_embeddings.get(w, np.zeros(100)) for w in words]
                v = np.mean(vectors, axis=0)
            else:
                v = np.zeros(100)
            sentence_vectors.append(v)
        return sentence_vectors

    def compute_similarity_matrix(self, sentence_vectors):
        """Compute cosine similarity matrix."""
        n = len(sentence_vectors)
        sim_mat = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    sim_mat[i][j] = cosine_similarity(
                        sentence_vectors[i].reshape(1, -1),
                        sentence_vectors[j].reshape(1, -1)
                    )[0, 0]
        return sim_mat

    def rank_sentences(self, sim_mat):
        """Rank sentences using PageRank."""
        nx_graph = nx.from_numpy_array(sim_mat)
        scores = nx.pagerank(nx_graph)
        return scores

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

def main():
    summarizer = TextSummarizer()
    df = summarizer.load_data()
    if df.empty:
        return

    scored_sentences = summarizer.run_summarization(df)

    while True:
        choice = input("Enter 'S' for a particular article or 'M' for all articles: ").upper()
        if choice == 'S':
            try:
                article_id = int(input("Enter Article ID: "))
                article_text, summary = summarizer.summarize_article(scored_sentences, article_id, df)
                if article_text and summary:
                    print("ARTICLE:")
                    print(article_text)
                    print('\nSUMMARY:')
                    print(summary)
                else:
                    print(f"Article ID {article_id} not found.")
            except ValueError:
                print("Invalid Article ID.")
            break
        elif choice == 'M':
            summaries = summarizer.summarize_all_articles(scored_sentences, df)
            for article_id, data in summaries.items():
                print(f"Processing Article ID: {article_id}")
                print("ARTICLE:")
                print(data['article'])
                print('\nSUMMARY:')
                print(data['summary'])
                print('\n')
            break
        else:
            print("Invalid choice. Please enter 'S' or 'M'.")

if __name__ == "__main__":
    main()