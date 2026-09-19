"""Authenticated, scale-to-zero GPU fallback for private advocates.
Deploy: modal deploy infra/modal_inference.py
Smoke test: modal run infra/modal_inference.py
"""
import modal

app=modal.App('proofpact-inference')
image=modal.Image.debian_slim(python_version='3.12').pip_install('torch==2.6.0','transformers==4.51.3','accelerate==1.6.0','huggingface-hub>=0.30,<1')
cache=modal.Volume.from_name('proofpact-model-cache',create_if_missing=True)

@app.cls(image=image,cpu=8,memory=16384,volumes={'/models':cache},timeout=180,scaledown_window=60,max_containers=1)
class Advocate:
    @modal.enter()
    def load(self):
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM
        model='Qwen/Qwen2.5-3B-Instruct'
        torch.set_num_threads(8)
        self.tokenizer=AutoTokenizer.from_pretrained(model,cache_dir='/models')
        self.model=AutoModelForCausalLM.from_pretrained(model,cache_dir='/models',torch_dtype=torch.float32,device_map='cpu')
        cache.commit()
    @modal.method()
    def generate(self,system:str,payload:str):
        import torch
        if len(payload)>16000 or len(system)>6000: raise ValueError('Context limit exceeded')
        prompt=self.tokenizer.apply_chat_template([{'role':'system','content':system},{'role':'user','content':payload}],tokenize=False,add_generation_prompt=True)
        inputs=self.tokenizer(prompt,return_tensors='pt').to(self.model.device)
        with torch.inference_mode():
            tokens=self.model.generate(**inputs,max_new_tokens=300,do_sample=False,pad_token_id=self.tokenizer.eos_token_id)
        text=self.tokenizer.decode(tokens[0][inputs['input_ids'].shape[1]:],skip_special_tokens=True)
        return {'text':text,'provider':'modal','model':'Qwen/Qwen2.5-3B-Instruct'}

@app.local_entrypoint()
def main():
    result=Advocate().generate.remote('Return only valid JSON.','Return {"ready":true}.')
    print(result)
