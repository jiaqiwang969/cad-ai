import requests
import base64

# 设置 API 密钥和自定义 URL
API_KEY = "sk-YgL2cnnuifh9AloZFa6d63111aC64e4898Ba0769077521Ac"
BASE_URL = "https://ai.pumpkinai.online/v1"

# 编码图片为 base64
def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# 构造请求体
image_b64 = encode_image("results/captcha_samples/results/captcha_samples/pre_solve_page_k_1748704900.png")
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
json_data = {
    "model": "gpt-4o",  # 确保该代理支持 gpt-4o 或 vision 模型
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Please extract and return only the text from this image. Output the exact 4 characters only, without any explanation or extra content."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]
        }
    ],
    "max_tokens": 10,
    "temperature": 0
}

# 发送 POST 请求
response = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=json_data)

# 打印结果
if response.ok:
    result = response.json()
    print("CAPTCHA result:", result['choices'][0]['message']['content'].strip())
else:
    print("❌ Error:", response.status_code, response.text)
