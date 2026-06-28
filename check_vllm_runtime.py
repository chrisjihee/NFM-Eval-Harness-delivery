"""vLLM runtime validator — proves real LLM(...).generate(), not just import.

Success is defined as: LLM object constructs AND generate() returns non-empty
text for >=1 prompt, with no traceback. Import success alone is NOT sufficient.

Records: torch CUDA state, vLLM version, the resolved libcudart path actually
loaded (cu12 vs cu13), LD_LIBRARY_PATH, generation output, elapsed time, GPU
memory, and full traceback on failure.

Usage:
    python scripts/check_vllm_runtime.py \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --max-model-len 2048 --gpu-memory-utilization 0.35 \
        --enforce-eager --tensor-parallel-size 1
Exit code 0 only if generate() succeeds with non-empty output.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback


def _loaded_cudart() -> str:
    """Read /proc/self/maps to see which libcudart.so is actually mapped."""
    try:
        hits = set()
        with open("/proc/self/maps", encoding="utf-8") as fh:
            for line in fh:
                if "libcudart.so" in line:
                    hits.add(line.split()[-1])
        return ";".join(sorted(hits)) or "(none mapped yet)"
    except Exception as e:  # pragma: no cover
        return f"(maps unreadable: {e})"


def main() -> int:
    ap = argparse.ArgumentParser(description="vLLM runtime generate-level validator")
    ap.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    ap.add_argument("--max-model-len", type=int, default=2048)
    ap.add_argument("--gpu-memory-utilization", type=float, default=0.35)
    ap.add_argument("--enforce-eager", action="store_true")
    ap.add_argument("--tensor-parallel-size", type=int, default=1)
    ap.add_argument("--max-tokens", type=int, default=16)
    ap.add_argument("--label", default="", help="free-form tag for the run (e.g. condition B)")
    args = ap.parse_args()

    report: dict[str, object] = {"label": args.label, "model": args.model}
    print(f"[check_vllm_runtime] label={args.label!r} model={args.model}")
    print(f"[env] LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH','')}")
    print(f"[env] VLLM_ATTENTION_BACKEND={os.environ.get('VLLM_ATTENTION_BACKEND','(unset)')}")
    print(f"[env] VLLM_USE_V1={os.environ.get('VLLM_USE_V1','(unset)')}")

    # 1) torch CUDA
    try:
        import torch
        report["torch_version"] = torch.__version__
        report["torch_cuda"] = torch.version.cuda
        report["cuda_available"] = torch.cuda.is_available()
        print(f"[torch] {torch.__version__} cuda={torch.version.cuda} available={torch.cuda.is_available()}")
        if torch.cuda.is_available():
            torch.zeros(8, device="cuda")  # force a real CUDA context
            print(f"[torch] cudart mapped after alloc: {_loaded_cudart()}")
    except Exception:
        report["torch_error"] = traceback.format_exc()
        print("[torch] FAILED:\n" + report["torch_error"])  # type: ignore[index]
        print("RESULT " + json.dumps(report, ensure_ascii=False))
        return 2

    # 2) vLLM import
    try:
        import vllm
        from vllm import LLM, SamplingParams
        report["vllm_version"] = vllm.__version__
        print(f"[vllm] import OK version={vllm.__version__}")
    except Exception:
        report["vllm_import_error"] = traceback.format_exc()
        print("[vllm] IMPORT FAILED:\n" + report["vllm_import_error"])  # type: ignore[index]
        print("RESULT " + json.dumps(report, ensure_ascii=False))
        return 3

    # 3) LLM init + generate (the real test)
    t0 = time.time()
    try:
        llm = LLM(
            model=args.model,
            max_model_len=args.max_model_len,
            gpu_memory_utilization=args.gpu_memory_utilization,
            enforce_eager=args.enforce_eager,
            tensor_parallel_size=args.tensor_parallel_size,
            trust_remote_code=True,
        )
        report["llm_init_success"] = True
        report["cudart_after_init"] = _loaded_cudart()
        print(f"[vllm] LLM init OK in {time.time()-t0:.1f}s; cudart={report['cudart_after_init']}")
        sp = SamplingParams(temperature=0.0, max_tokens=args.max_tokens)
        prompts = ["The capital of France is", "2 + 2 ="]
        outs = llm.generate(prompts, sp)
        texts = [o.outputs[0].text if o.outputs else "" for o in outs]
        report["generate_success"] = all(t.strip() for t in texts)
        report["generated"] = texts
        report["elapsed_s"] = round(time.time() - t0, 2)
        try:
            import torch as _t
            report["gpu_mem_alloc_mb"] = round(_t.cuda.max_memory_allocated() / 1e6, 1)
        except Exception:
            pass
        print(f"[vllm] generate -> {texts}")
        ok = bool(report["generate_success"])
        print(f"[vllm] generate_success={ok} elapsed={report['elapsed_s']}s")
        print("RESULT " + json.dumps(report, ensure_ascii=False))
        return 0 if ok else 4
    except Exception:
        report["llm_or_generate_error"] = traceback.format_exc()
        print("[vllm] LLM/generate FAILED:\n" + report["llm_or_generate_error"])  # type: ignore[index]
        print("RESULT " + json.dumps(report, ensure_ascii=False))
        return 5


if __name__ == "__main__":
    sys.exit(main())
