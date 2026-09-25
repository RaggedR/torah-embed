"""Refuse to start heavy work when memory is tight. Import and call require(gb)."""
import subprocess,sys,re
def free_gb():
    try:
        out=subprocess.run(['vm_stat'],capture_output=True,text=True).stdout
        page=int(re.search(r'page size of (\d+)',out).group(1))
        def g(k):
            m=re.search(rf'{k}:\s+(\d+)',out); return int(m.group(1))*page/1073741824 if m else 0
        return g('Pages free')+g('Pages inactive')+g('Pages purgeable')
    except Exception: return 99.0
def require(gb,label=''):
    f=free_gb()
    print(f"[memguard] {f:.1f} GB available, need {gb:.1f} GB {label}",flush=True)
    if f < gb:
        print(f"[memguard] REFUSING TO START — close other work first",flush=True)
        sys.exit(9)
    return f
if __name__=='__main__': print(f"{free_gb():.1f} GB available")
