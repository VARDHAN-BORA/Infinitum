import os
from datasets import load_dataset

output_dir = "data/documents"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Connecting to Hugging Face Hub...")
# Updated dataset name to include the explicit namespace to satisfy the URI parser
dataset = load_dataset("fancyzhx/ag_news", split="train")

print(f"📦 Successfully connected! Extracting articles to {output_dir}...")

max_documents = 200

for index in range(max_documents):
    row = dataset[index]
    text_content = row["text"]
    
    filename = f"real_world_doc_{index + 1}.txt"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("REAL WORLD CORPORATE INTELLIGENCE FEED\n")
        f.write(f"Document Reference Identifier: REF-{1000 + index}\n\n")
        f.write(text_content)
        f.write("\n\nOperational Standard Compliance: All workflows mapping to this ledger entry require ")
        f.write("rigorous infrastructure logging, token metric valuation, and decoupled Redis cache validation.")
        
    if (index + 1) % 50 == 0:
        print(f"✅ Generated {index + 1} / {max_documents} real-world data files.")

print(f"\n🎉 Done! Your '{output_dir}' folder contains real-world text data ready for massive RAG ingestion.")
