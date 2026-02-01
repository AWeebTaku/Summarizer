import argparse
from .summarizer import TextSummarizer

def main():
    parser = argparse.ArgumentParser(description="Text Summarization Tool")
    parser.add_argument("--glove-path", default="glove.6B.100d.txt/glove.6B.100d.txt",
                        help="Path to GloVe embeddings file")
    parser.add_argument("--num-sentences", type=int, default=5,
                        help="Number of sentences in summary")
    parser.add_argument("--csv-file", help="Path to CSV file with articles")
    parser.add_argument("--article-id", type=int, help="Article ID to summarize (if CSV provided)")
    parser.add_argument("--gui", action="store_true", help="Launch graphical user interface")

    args = parser.parse_args()

    if args.gui:
        # Import and run GUI
        from .ui import main as gui_main
        gui_main()
        return

    try:
        summarizer = TextSummarizer(glove_path=args.glove_path, num_sentences=args.num_sentences)

        if args.csv_file:
            import pandas as pd
            df = pd.read_csv(args.csv_file)
            scored_sentences = summarizer.run_summarization(df)

            if args.article_id:
                article_text, summary = summarizer.summarize_article(scored_sentences, args.article_id, df)
                if article_text and summary:
                    print("ARTICLE:")
                    print(article_text)
                    print('\nSUMMARY:')
                    print(summary)
                else:
                    print(f"Article ID {args.article_id} not found.")
            else:
                summaries = summarizer.summarize_all_articles(scored_sentences, df)
                for article_id, data in summaries.items():
                    print(f"Processing Article ID: {article_id}")
                    print("ARTICLE:")
                    print(data['article'])
                    print('\nSUMMARY:')
                    print(data['summary'])
                    print('\n')
        else:
            # Interactive mode
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

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()