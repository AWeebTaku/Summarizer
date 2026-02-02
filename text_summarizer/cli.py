import argparse
from .summarizer import TextSummarizer

def main():
    parser = argparse.ArgumentParser(
        description="Text Summarization Tool",
        epilog="""
Examples:
  text-summarizer-aweebtaku --csv-file data.csv --article-id 1
  text-summarizer-aweebtaku --gui

Desktop Shortcuts (Windows):
  text-summarizer-shortcuts    # Create desktop shortcuts
  text-summarizer-gui         # Launch graphical interface

Upgrade:
  pip install --upgrade text-summarizer-aweebtaku
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

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