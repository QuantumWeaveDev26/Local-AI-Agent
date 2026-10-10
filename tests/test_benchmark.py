from types import SimpleNamespace
from app.main import ollama_rss_gib


def test_benchmark_counts_inference_runner_children(monkeypatch):
    processes=[SimpleNamespace(info={'pid':10,'ppid':1,'name':'ollama','memory_info':SimpleNamespace(rss=2**30)}),SimpleNamespace(info={'pid':11,'ppid':10,'name':'llama-server','memory_info':SimpleNamespace(rss=2*2**30)}),SimpleNamespace(info={'pid':12,'ppid':1,'name':'unrelated','memory_info':SimpleNamespace(rss=8*2**30)})]
    monkeypatch.setattr('app.main.psutil.process_iter',lambda fields:iter(processes))
    assert ollama_rss_gib()==3
