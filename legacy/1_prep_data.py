import pandas as pd

print("Loading the master CSV...")
df = pd.read_csv("master_chats.csv")
df = df.dropna(subset=['Message'])

paired_data = []
current_user_msg = ""
current_date = ""
current_title = ""

print("Pairing user prompts and AI responses into semantic blocks...")
for index, row in df.iterrows():
    if row['Role'] == 'user':
        current_user_msg = row['Message']
        current_date = row['Date']
        current_title = row['Chat Title']
    elif row['Role'] == 'assistant' and current_user_msg:
        # Pair user message with AI response into a single semantic block
        combined_message = f"USER ASKED: {current_user_msg}\nAI ANSWERED: {row['Message']}"
        paired_data.append({
            "Date": current_date,
            "Chat Title": current_title,
            "Message": combined_message
        })
        current_user_msg = "" # Reset for the next pair

paired_df = pd.DataFrame(paired_data)
paired_df.to_csv("paired_chats.csv", index=False)
print(f"Done! Squashed {len(df)} lines down to {len(paired_df)} highly contextual memory blocks.")