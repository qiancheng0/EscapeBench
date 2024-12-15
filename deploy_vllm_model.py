from flask import Flask, request, jsonify
from vllm import LLM, SamplingParams

app = Flask(__name__)

# Load the vLLM model
llm = LLM(
    model="path/to/your/model",
    tensor_parallel_size=2,  # Adjust based on your hardware
    dtype="bfloat16",
    max_model_len=2400,
    gpu_memory_utilization=0.9,
    trust_remote_code=True
)

@app.route("/predict", methods=["POST"])
def predict():
    """API endpoint to get predictions from the vLLM model."""
    data = request.json
    if not data or "sys_prompt" not in data or "user_prompt" not in data:
        return jsonify({"error": "Missing input_text field"}), 400
    
    sys_prompt = data["sys_prompt"]
    user_prompt = data["user_prompt"]
    
    # Combine system and user messages into a single input
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        # Generate a response with vLLM
        sampling_params = SamplingParams(
            max_tokens=256,
            temperature=0
        )
        result = llm.chat(messages, sampling_params=sampling_params)
        print(result)
        # Extract the generated text
        generated_text = result[0].outputs[0].text.strip()
        return jsonify({"prediction": generated_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def call_model_server(sys_prompt: str, user_prompt: str, port: str) -> str:
    import requests
    server_url = f"http://127.0.0.1:{port}/predict"
    try:
        response = requests.post(server_url, json={"sys_prompt": sys_prompt, "user_prompt": user_prompt})
        response.raise_for_status()
        res = response.json()["prediction"]
        return res
    except requests.exceptions.RequestException as e:
        return f"Error connecting to the server: {e}"


if __name__ == "__main__":
    port = 12345 # Choose an unused port number
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
