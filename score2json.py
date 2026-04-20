import requests

# 1. Your n8n Webhook URL
# Make sure your n8n node is set to HTTP Method: POST
N8N_URL = "https://autotuto.app.n8n.cloud/webhook-test/a44c387d-f012-49d4-86a2-c7ec43c6774a"

def send_score_to_n8n(file_path):
    try:
        # 2. Open the file in Binary Read mode ('rb')
        with open(file_path, 'rb') as image_file:
            
            # 3. Define the 'files' dictionary 
            # 'data' is the key n8n will look for in the Binary Property
            files = {'data': (file_path, image_file, 'image/png')}
            
            print(f"🚀 Sending {file_path} to n8n...")
            
            # 4. Execute the POST request
            response = requests.post(N8N_URL, files=files)
            
            # 5. Check if it worked
            if response.status_code == 200:
                print("✅ Success!")
                print("Result from n8n:", response.text)
                return response.text
            else:
                print(f"❌ Failed with status code: {response.status_code}")
                print("Error detail:", response.text)
                return None

    except FileNotFoundError:
        print("Error: The file was not found at the specified path.")

# --- RUN IT ---
# Replace 'score2.png' with your actual filename
grid_result = send_score_to_n8n('score2.png')