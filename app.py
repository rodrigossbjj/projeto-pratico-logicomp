# app.py
import os
import shlex
import sys
import subprocess
import importlib.util
import inspect
from flask import Flask, render_template, request, Response, stream_with_context
from typing import Iterable

app = Flask(__name__)
ROOT = os.path.dirname(__file__)

# helper: convert generator/iterable into SSE text/event-stream
def sse_wrap(iterable: Iterable[str]):
    for item in iterable:
        text = str(item).rstrip("\n")
        # SSE data: lines must be prefixed with "data:"
        yield f"data: {text}\n\n"
    # end event
    yield "event: done\ndata: done\n\n"

def run_module_as_subprocess(module_name: str, args: str = ""):
    """Run python -m <module_name> or python <module_name>.py as subprocess and yield stdout lines."""
    # Try to run file by name if exists
    file_py = os.path.join(ROOT, f"{module_name}.py")
    if os.path.exists(file_py):
        cmd = [sys.executable, file_py] + (shlex.split(args) if args else [])
    else:
        # try python -m module
        cmd = [sys.executable, "-m", module_name] + (shlex.split(args) if args else [])

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
    finally:
        try:
            proc.stdout.close()
        except:
            pass
        proc.wait()

def import_module_solve(module_name: str):
    """Try to import module_name.py from project root and return a callable solve() if present."""
    file_path = os.path.join(ROOT, f"{module_name}.py")
    if not os.path.exists(file_path):
        return None
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Import error for {module_name}: {e}", file=sys.stderr)
        return None

    # Prefer function named 'solve'
    fn = getattr(module, "solve", None)
    if fn and callable(fn):
        return fn
    # fallback: look for 'main' or 'run'
    for name in ("main", "run"):
        fn = getattr(module, name, None)
        if fn and callable(fn):
            return fn
    return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/stream")
def stream():
    """
    SSE stream endpoint.
    Query params:
      - module: module filename without .py (default: main)
      - args: optional args string to pass to the module/function
    """
    module = request.args.get("module", "main")
    args = request.args.get("args", "")

    solver_fn = import_module_solve(module)

    if solver_fn:
        def gen():
            # Try calling with args if signature accepts parameters
            try:
                sig = inspect.signature(solver_fn)
                if len(sig.parameters) == 0:
                    result = solver_fn()
                else:
                    # pass raw args string (user can interpret)
                    result = solver_fn(args)
            except Exception as e:
                # If calling raised, yield error and stop
                yield f"ERROR when calling {module}.solve(): {e}"
                return

            # If result is iterable, yield items; else yield single str
            if hasattr(result, "__iter__") and not isinstance(result, (str, bytes)):
                for s in result:
                    yield s
            else:
                yield str(result)

        return Response(stream_with_context(sse_wrap(gen())), mimetype="text/event-stream")

    # fallback: run module as subprocess and stream stdout lines
    def proc_gen():
        try:
            for line in run_module_as_subprocess(module, args):
                yield line
        except Exception as e:
            yield f"ERROR running subprocess: {e}"

    return Response(stream_with_context(sse_wrap(proc_gen())), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
