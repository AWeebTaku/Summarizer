import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import threading
from textsummarization import TextSummarizer


class TextSummarizerUI:
    """A GUI application for text summarization."""

    def __init__(self, root):
        self.root = root
        self.root.title("Text Summarizer")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        self.root.configure(bg='#f0f0f0')

        # Configure styles
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 10))
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TFrame', background='#f0f0f0')

        self.summarizer = None
        self.df = None
        self.scored_sentences = None
        self.is_single = False

        self.create_widgets()

    def create_widgets(self):
        """Create and layout all UI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Text Summarizer", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Data loading section
        load_frame = ttk.LabelFrame(main_frame, text="Load Data", padding="10")
        load_frame.pack(fill=tk.X, pady=10)

        ttk.Button(load_frame, text="Paste Single Document", command=self.paste_single).pack(side=tk.LEFT, padx=5)
        ttk.Button(load_frame, text="Upload CSV", command=self.upload_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(load_frame, text="Create CSV", command=self.create_csv).pack(side=tk.LEFT, padx=5)

        # Status
        self.status_label = ttk.Label(main_frame, text="Ready to load data")
        self.status_label.pack(pady=5)

        # Summarization section
        self.sum_frame = ttk.LabelFrame(main_frame, text="Summarization", padding="10")
        self.sum_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.update_summarization_ui()

        # Results display
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Original document display
        original_frame = ttk.Frame(results_frame)
        original_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        label_frame = ttk.Frame(original_frame)
        label_frame.pack(fill=tk.X)
        ttk.Label(label_frame, text="Original Document:").pack(side=tk.LEFT)
        ttk.Button(label_frame, text="View Full", command=self.view_original).pack(side=tk.RIGHT)
        self.original_text = scrolledtext.ScrolledText(original_frame, wrap=tk.WORD, height=8)
        self.original_text.pack(fill=tk.BOTH, expand=True)
        self.original_text.config(state='disabled')

        # Summary display
        summary_frame = ttk.Frame(results_frame)
        summary_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        label_frame2 = ttk.Frame(summary_frame)
        label_frame2.pack(fill=tk.X)
        ttk.Label(label_frame2, text="Summary:").pack(side=tk.LEFT)
        ttk.Button(label_frame2, text="View Full", command=self.view_summary).pack(side=tk.RIGHT)
        self.summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, height=8)
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        self.summary_text.config(state='disabled')

        # Bottom frame for Clear All and Save Summaries buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=1)
        ttk.Button(bottom_frame, text="Save Summaries", command=self.save_summaries).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Clear All", command=self.clear_all).pack(side=tk.RIGHT, padx=5)

    def update_summarization_ui(self):
        """Update the summarization UI based on data type (single or multiple)."""
        # Clear existing widgets in sum_frame
        for widget in self.sum_frame.winfo_children():
            widget.destroy()

        if self.is_single:
            ttk.Button(self.sum_frame, text="Summarize", command=self.summarize_single).pack(side=tk.LEFT, padx=5)
        else:
            ttk.Button(self.sum_frame, text="Summarize Single Document", command=self.summarize_single).pack(side=tk.LEFT, padx=5)
            ttk.Button(self.sum_frame, text="Summarize All Documents", command=self.summarize_all).pack(side=tk.LEFT, padx=5)

            # Article ID input
            id_frame = ttk.Frame(self.sum_frame)
            id_frame.pack(side=tk.LEFT, padx=10)
            ttk.Label(id_frame, text="Document ID:").pack(side=tk.LEFT)
            self.article_id_entry = ttk.Entry(id_frame, width=10)
            self.article_id_entry.pack(side=tk.LEFT, padx=5)

    def save_summaries(self):
        """Save the generated summaries to a CSV file."""
        if self.scored_sentences is None or self.df is None:
            messagebox.showwarning("Warning", "No summaries to save. Please summarize first.")
            return
        if self.is_single:
            # Summarize the single document
            article_id = 1
            article_text, summary = self.summarizer.summarize_article(self.scored_sentences, article_id, self.df)
            data = [{"article_id": article_id, "article_text": article_text, "summary": summary}]
        else:
            # Summarize all documents
            summaries = self.summarizer.summarize_all_articles(self.scored_sentences, self.df)
            data = []
            for article_id, d in summaries.items():
                data.append({"article_id": article_id, "article_text": d["article"], "summary": d["summary"]})
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            try:
                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False)
                messagebox.showinfo("Success", f"Summaries saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save summaries: {str(e)}")

    def clear_all(self):
        """Clear all data and reset the UI."""
        self.is_single = False
        self.df = None
        self.scored_sentences = None
        self.summarizer = None
        self.status_label.config(text="Ready to load data")
        self.update_summarization_ui()
        self.original_text.config(state='normal')
        self.original_text.delete(1.0, tk.END)
        self.original_text.config(state='disabled')
        self.summary_text.config(state='normal')
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.config(state='disabled')

    def paste_single(self):
        """Open dialog to paste a single document."""
        dialog = PasteDialog(self.root)
        self.root.wait_window(dialog.top)
        if dialog.result:
            self.df = pd.DataFrame([{'article_id': 1, 'article_text': dialog.result}])
            self.is_single = True
            self.status_label.config(text="Single document loaded")
            self.update_summarization_ui()
            self.initialize_summarizer()

    def upload_csv(self):
        """Upload and load a CSV file with documents."""
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            try:
                self.df = pd.read_csv(file_path)
                self.is_single = False
                self.status_label.config(text=f"CSV loaded from {file_path}")
                self.update_summarization_ui()
                self.initialize_summarizer()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")

    def create_csv(self):
        """Open dialog to create a new CSV with multiple documents."""
        dialog = CreateCSVDialog(self.root)
        self.root.wait_window(dialog.top)
        if dialog.result:
            self.df = pd.DataFrame(dialog.result)
            self.is_single = False
            self.status_label.config(text="CSV created")
            self.update_summarization_ui()
            self.initialize_summarizer()

    def initialize_summarizer(self):
        """Initialize the summarizer and start processing data in a thread."""
        if self.df is not None and not self.df.empty:
            self.summarizer = TextSummarizer()
            self.status_label.config(text="Processing data...")
            threading.Thread(target=self.process_data).start()

    def process_data(self):
        """Process the data to compute sentence scores."""
        try:
            self.scored_sentences = self.summarizer.run_summarization(self.df)
            self.status_label.config(text="Data processed successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed: {str(e)}")

    def summarize_single(self):
        """Summarize a single document."""
        if self.scored_sentences is None:
            messagebox.showwarning("Warning", "Please load and process data first")
            return
        if self.is_single:
            article_id = 1
        else:
            try:
                article_id = int(self.article_id_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid Document ID")
                return
        article_text, summary = self.summarizer.summarize_article(self.scored_sentences, article_id, self.df)
        if article_text and summary:
            self.display_result(article_text, summary)
        else:
            messagebox.showerror("Error", f"Document ID {article_id} not found")

    def summarize_all(self):
        """Summarize all documents and display in text areas."""
        if self.scored_sentences is None:
            messagebox.showwarning("Warning", "Please load and process data first")
            return
        summaries = self.summarizer.summarize_all_articles(self.scored_sentences, self.df)
        self.original_text.config(state='normal')
        self.summary_text.config(state='normal')
        self.original_text.delete(1.0, tk.END)
        self.summary_text.delete(1.0, tk.END)
        for article_id, data in summaries.items():
            self.original_text.insert(tk.END, f"Document ID: {article_id}\n{data['article']}\n\n")
            self.summary_text.insert(tk.END, f"Document ID: {article_id}\n{data['summary']}\n\n")
        self.original_text.config(state='disabled')
        self.summary_text.config(state='disabled')

    def display_result(self, article, summary):
        """Display the article and summary in the text areas."""
        self.original_text.config(state='normal')
        self.original_text.delete(1.0, tk.END)
        self.original_text.insert(tk.END, article)
        self.original_text.config(state='disabled')
        self.summary_text.config(state='normal')
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, summary)
        self.summary_text.config(state='disabled')

    def view_original(self):
        """Open a full view window for the original document."""
        top = tk.Toplevel(self.root)
        top.title("Original Document - Full View")
        top.geometry("900x700")
        top.resizable(True, True)
        text = scrolledtext.ScrolledText(top, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, self.original_text.get(1.0, tk.END))
        text.config(state=tk.DISABLED)  # Make it read-only

    def view_summary(self):
        """Open a full view window for the summary."""
        top = tk.Toplevel(self.root)
        top.title("Summary - Full View")
        top.geometry("900x700")
        top.resizable(True, True)
        text = scrolledtext.ScrolledText(top, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, self.summary_text.get(1.0, tk.END))
        text.config(state=tk.DISABLED)  # Make it read-only

class PasteDialog:
    """Dialog for pasting a single document."""

    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Paste Document")
        self.top.geometry("700x600")
        self.top.transient(parent)
        self.top.grab_set()
        self.result = None

        ttk.Label(self.top, text="Paste your document:").pack(pady=5)
        self.text = scrolledtext.ScrolledText(self.top, wrap=tk.WORD)
        self.text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        button_frame = ttk.Frame(self.top)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=5)

    def ok(self):
        self.result = self.text.get(1.0, tk.END).strip()
        self.top.destroy()

    def cancel(self):
        self.top.destroy()

class CreateCSVDialog:
    """Dialog for creating a CSV with multiple documents."""

    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Create CSV")
        self.top.geometry("700x600")
        self.top.transient(parent)
        self.top.grab_set()
        self.result = []

        self.articles = []
        self.counter = 1

        ttk.Label(self.top, text="Enter documents (ID and text):").pack(pady=5)

        input_frame = ttk.Frame(self.top)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(input_frame, text="Document ID:").grid(row=0, column=0, sticky=tk.W)
        self.id_entry = ttk.Entry(input_frame, width=10)
        self.id_entry.grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Document Text:").grid(row=1, column=0, sticky=tk.W)
        self.text_entry = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=5)
        self.text_entry.grid(row=1, column=1, padx=5, pady=5)

        button_frame = ttk.Frame(self.top)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(button_frame, text="Add Document", command=self.add_article).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Done", command=self.done).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=5)

        self.listbox = tk.Listbox(self.top, height=10)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def add_article(self):
        try:
            article_id = int(self.id_entry.get())
            article_text = self.text_entry.get(1.0, tk.END).strip()
            if article_text:
                self.articles.append({'article_id': article_id, 'article_text': article_text})
                self.listbox.insert(tk.END, f"ID: {article_id} - {article_text[:50]}...")
                self.id_entry.delete(0, tk.END)
                self.text_entry.delete(1.0, tk.END)
                self.counter += 1
                self.id_entry.insert(0, str(self.counter))
            else:
                messagebox.showwarning("Warning", "Document cannot be empty")
        except ValueError:
            messagebox.showerror("Error", "Invalid Document ID")

    def done(self):
        if self.articles:
            save = messagebox.askyesno("Save CSV", "Do you want to save the CSV file?")
            if save:
                file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
                if file_path:
                    df = pd.DataFrame(self.articles)
                    df.to_csv(file_path, index=False)
                    try:
                        loaded_df = pd.read_csv(file_path)
                        self.result = loaded_df.to_dict(orient='records')
                    except Exception:
                        self.result = self.articles
                else:
                    self.result = self.articles
            else:
                self.result = self.articles
        self.top.destroy()

    def cancel(self):
        self.top.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TextSummarizerUI(root)
    root.mainloop()