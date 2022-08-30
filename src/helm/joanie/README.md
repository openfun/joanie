# Joanie Helm Chart 

This chart's aims is to deploy the Joanie project in a kubernetes cluster.

## Testing 

To test this chart, a local kubernetes environment is needed (`k3d` for example).

Once the kubernetes cluster is up and running, you need to [install Helm](https://helm.sh/docs/intro/install/). 

Once Helm is installed, make sure that the environement variable `$KUBECONFIG` is set (if you are using `k3d`, you can do this with `export KUBECONFIG=$(k3d kubeconfig write <name-of-your-cluster> )`).

To install this chart and deploy the project, you need to launch this command:

```bash
$ helm install <name-of-release> <helm-chart-directory>
```

For example:
 
```bash
$ helm install joanie src/helm/joanie
```
