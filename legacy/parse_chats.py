import json
import csv
import os
from datetime import datetime

def extract_multiple_chatgpt_files(file_prefix, num_files, output_csv_path):
    print("Initializing the data harvester... now with Time Travel enabled ⏱️")
    extracted_messages = []
    
    for i in range(1, num_files + 1):
        file_name = f"{file_prefix}-{i}.json"
        print(f"Loading {file_name}...")
        
        if not os.path.exists(file_name):
            print(f"  -> Skipping {file_name} (Not found).")
            continue
            
        with open(file_name, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
        if isinstance(data, dict):
            data = [data]
            
        for conversation in data:
            title = conversation.get("title", "Untitled Conversation")
            mapping = conversation.get("mapping", {})

            for node_id, node_data in mapping.items():
                message = node_data.get("message")
                
                if message:
                    author_role = message.get("author", {}).get("role")
                    
                    if author_role in ["user", "assistant"]:
                        # --- NEW: Time Extraction ---
                        raw_time = message.get("create_time")
                        if raw_time:
                            # Convert Unix timestamp to a readable date/time
                            readable_date = datetime.fromtimestamp(raw_time).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            readable_date = "Unknown Date"
                            
                        content_parts = message.get("content", {}).get("parts", [])
                        
                        text_content = ""
                        for part in content_parts:
                            if isinstance(part, str):
                                text_content += part + "\n"

                        if text_content.strip():
                            extracted_messages.append({
                                "Date": readable_date,  # Added to our dataset!
                                "Chat Title": title,
                                "Role": author_role,
                                "Message": text_content.strip()
                            })
                            
    print(f"\nExtraction complete! Found {len(extracted_messages)} time-stamped messages.")
    print(f"Saving to {output_csv_path}...")
    
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Date', 'Chat Title', 'Role', 'Message']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(extracted_messages)
        
    print("Done! Your master CSV now understands the flow of time.")

# Run it!
extract_multiple_chatgpt_files('conversations', 3, 'master_chats.csv')