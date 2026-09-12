# Despliegue de ShopApi en Cloud Run

El workflow `.github/workflows/deploy-cloud-run.yml` despliega según el prefijo
del tag:

- `dev-*` usa el environment de GitHub `development`.
- `prod-*` usa el environment de GitHub `production`.

Los tags exactos `dev` y `prod` también funcionan una vez, pero para despliegues
repetibles se recomienda usar tags versionados como `dev-1.0.0` y `prod-1.0.0`.

## Recursos de GCP

Habilitar APIs y crear un repositorio Docker:

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com iamcredentials.googleapis.com

gcloud artifacts repositories create shop-api \
  --repository-format=docker \
  --location=us-central1
```

Crear tres secretos diferentes para development y production:

```bash
printf '%s' 'store.myshopify.com' | gcloud secrets create shopify-shop-dev --data-file=-
printf '%s' 'client-id' | gcloud secrets create shopify-api-key-dev --data-file=-
printf '%s' 'client-secret' | gcloud secrets create shopify-api-secret-dev --data-file=-
```

Repetir para producción usando nombres terminados en `-prod`. No guardar los
valores en GitHub ni en archivos versionados.

## Autenticación de GitHub

Configurar Workload Identity Federation restringiendo el proveedor al repositorio
GitHub correspondiente. La cuenta de despliegue necesita como mínimo permisos
para publicar en Artifact Registry, desplegar Cloud Run, actuar como la identidad
de ejecución y asociar secretos al servicio.

La identidad de ejecución de Cloud Run necesita `roles/secretmanager.secretAccessor`
sobre los seis secretos. Evitar claves JSON permanentes de cuentas de servicio.

## Variables de GitHub

Crear los environments `development` y `production` en GitHub y definir estas
variables en cada uno:

| Variable | Ejemplo development |
|---|---|
| `GCP_PROJECT_ID` | `my-gcp-project` |
| `GCP_REGION` | `us-central1` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/123/locations/global/workloadIdentityPools/github/providers/repository` |
| `GCP_SERVICE_ACCOUNT` | `github-deployer@my-gcp-project.iam.gserviceaccount.com` |
| `ARTIFACT_REGISTRY_REPOSITORY` | `shop-api` |
| `CLOUD_RUN_SERVICE` | `shop-api-dev` |
| `SHOPIFY_SHOP_SECRET` | `shopify-shop-dev` |
| `SHOPIFY_API_KEY_SECRET` | `shopify-api-key-dev` |
| `SHOPIFY_API_SECRET_SECRET` | `shopify-api-secret-dev` |

En production usar, por ejemplo, `shop-api-prod` y los secretos terminados en
`-prod`. Se puede exigir aprobación manual para el environment `production`
mediante las deployment protection rules de GitHub.

## Desplegar

```bash
git tag dev-1.0.0
git push origin dev-1.0.0
```

Después de validar development:

```bash
git tag prod-1.0.0
git push origin prod-1.0.0
```

El servicio queda privado por defecto. La primera configuración pública, si se
necesita, debe realizarse explícitamente mediante IAM de Cloud Run; los futuros
despliegues conservan dicha política.
