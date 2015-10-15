import dcos
import os

def main():
    import dcos_kubernetes
    dcos_kubernetes.main()

if __name__ == "__main__":
    cfg = os.path.join(os.getenv("HOME"), dcos.constants.DCOS_DIR, "dcos.toml")
    os.environ[dcos.constants.DCOS_CONFIG_ENV] = cfg
    main()