import json
import random

# File paths
system_prompt_path = "/home/dragon/Apps/PUBLIC_GITHUB_BEACON/beacon/prompts/coestral_RULAC_neo_systemOPT_SYNTHCLEAN4MISTRA_CUT.md"
data_path = "/home/dragon/Apps/PUBLIC_GITHUB_BEACON/beacon/pipeline_results_MASTER_V3.json"
train_output_path = "/home/dragon/Apps/PUBLIC_GITHUB_BEACON/beacon/formatted_unsloth_train_V3.jsonl"
val_output_path = "/home/dragon/Apps/PUBLIC_GITHUB_BEACON/beacon/formatted_unsloth_val_V3.jsonl"

# Read system prompt
with open(system_prompt_path, "r", encoding="utf-8") as f:
    system_prompt = f.read().strip()

# Read input JSON file
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Prepare formatted dataset with two columns: instruction and output
formatted_data = []
for entry in data:
    # Merge system prompt and user input into one instruction prompt.
    # You can customize the format below as needed.
    merged_instruction = f"{system_prompt}\n\nUSER research question: {entry['Input']}"
    
    formatted_data.append({
        "instruction": merged_instruction,
        "output": entry["Generated Query"]
    })

# Shuffle data for randomness
random.shuffle(formatted_data)

# Define split size (80% train, 20% validation)
split_index = int(len(formatted_data) * 0.8)
train_data = formatted_data[:split_index]
val_data = formatted_data[split_index:]

# Write training data to JSONL file
with open(train_output_path, "w", encoding="utf-8") as f_train:
    for item in train_data:
        f_train.write(json.dumps(item) + "\n")

# Write validation data to JSONL file
with open(val_output_path, "w", encoding="utf-8") as f_val:
    for item in val_data:
        f_val.write(json.dumps(item) + "\n")

print(f"Training dataset saved to {train_output_path} ({len(train_data)} examples)")
print(f"Validation dataset saved to {val_output_path} ({len(val_data)} examples)")
