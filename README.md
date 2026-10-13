# Python DevOps Platform — Jenkins Multibranch + GitFlow

Projet pédagogique de chaîne CI/CD complète : application Python/FastAPI, tests, qualité SonarQube,
contrôles de sécurité, image Docker publiée sur Docker Hub, infrastructure AWS par Terraform,
configuration et déploiement par Ansible.

> Le dépôt est un **squelette opérationnel à adapter**. Aucun déploiement AWS n'est lancé par ce projet.
> Renseignez les credentials Jenkins et vérifiez les coûts AWS avant d'activer les étapes de déploiement.

## 1. Architecture

```text
Git (main / develop / feature/* / release/* / hotfix/*)
                         |
                  Jenkins Multibranch
                         |
       lint -> unit -> integration -> coverage
                         |
       security (Bandit, pip-audit, Trivy FS)
                         |
                  SonarQube analysis
                         |
             performance smoke (Locust)
                         |
               Docker build + scan
                         |
               Docker Hub push (selon branche)
                         |
        Terraform plan/apply (environnements AWS)
                         |
             Ansible configure + deploy
```

## 2. GitFlow et comportement de la pipeline

| Branche | Comportement attendu |
|---|---|
| `feature/*` | lint, tests unitaires/intégration, couverture, sécurité, analyse Sonar ; pas de push d'image ni déploiement |
| `develop` | validations complètes, image tag `dev-<BUILD_NUMBER>`, push Docker Hub si autorisé |
| `release/*` | validations complètes, image tag `rc-<BUILD_NUMBER>`, push Docker Hub si autorisé |
| `main` | validations complètes, image versionnée, push ; déploiement production soumis à approbation |
| `hotfix/*` | validations complètes, image `hotfix-<BUILD_NUMBER>` ; pas de déploiement automatique de production |

Le `Jenkinsfile` utilise `when` pour sélectionner les étapes. Dans Jenkins, créez un **Multibranch Pipeline**
et configurez le scan du dépôt Git. Les noms de branches et les règles peuvent être ajustés à votre convention.

## 3. Prérequis

- Jenkins avec plugins : Pipeline, Git, Branch API, Credentials Binding, JUnit, HTML Publisher (optionnel), SonarQube Scanner.
- Agents Jenkins avec Docker, Python 3.12, Terraform, Ansible, AWS CLI, Trivy et `jq` installés.
- Un serveur SonarQube et un webhook SonarQube → Jenkins pour le Quality Gate.
- Credentials Jenkins :
  - `dockerhub-creds` : identifiant/mot de passe Docker Hub.
  - `sonar-token` : secret text du token SonarQube.
  - `aws-credentials` : credentials AWS (ou privilégier un rôle IAM attaché à l'agent).
  - `ansible-ssh-key` : clé SSH privée de l'utilisateur de déploiement.
- Pour les runners/agents AWS, préférer IAM Roles et Secrets Manager plutôt que des clés statiques.

## 4. Lancer localement

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell : .venv\\Scripts\\Activate.ps1

pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
pytest -m "not performance"
```

Test rapide : `curl http://127.0.0.1:8000/health`

## 5. Configuration Jenkins

Dans **Manage Jenkins → System**, configurez une installation SonarQube nommée `sonarqube`.
Dans le job Multibranch :
1. Ajouter la source Git.
2. Activer la découverte des branches et le scan périodique.
3. Définir les credentials Git si le dépôt est privé.
4. Vérifier que les outils sont disponibles sur l'agent (ou adapter `agent`/images d'agent).
5. Définir les variables globales `DOCKERHUB_USER`, `AWS_REGION` et `TF_VAR_*` si nécessaire.

Le pipeline suppose que le nom de credential Docker Hub est `dockerhub-creds`, le token Sonar `sonar-token`,
et que le projet Sonar est identifié par `python-devops-demo`. Ne jamais mettre de secrets dans le dépôt.

## 6. AWS / Terraform / Ansible

Les fichiers Terraform créent un VPC, un subnet public, un security group et une instance EC2.
La configuration par défaut est volontairement minimale pour un lab et doit être durcie avant usage réel.
Le port SSH est restreint à `var.admin_cidr`; remplacez la valeur par votre IP publique `/32`.
Le port 8000 est ouvert uniquement selon la variable `app_cidr` : en production, préférez un ALB HTTPS.
Le déploiement Ansible installe Docker et lance le conteneur sur l'instance.

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Modifier admin_cidr, app_cidr, key_name, ami_id et image
terraform init
terraform fmt -check
terraform validate
terraform plan
# Seulement après revue :
terraform apply
```

Après création, récupérez l'IP publique dans la sortie Terraform puis :

```bash
cd ../../infra/ansible
ansible-playbook -i inventory.ini deploy.yml \
  -e "target_host=<IP_PUBLIQUE>" \
  -e "docker_image=<dockerhub-user>/python-devops-demo:latest"
```

Adaptez la distribution AMI et le nom d'utilisateur SSH (`ec2-user` par défaut pour Amazon Linux).
Ne laissez pas `terraform.tfvars`, les clés privées ou les fichiers d'état Terraform dans Git.

## 7. Limitations et améliorations conseillées

- Le test de performance fourni est un smoke test Locust ; il ne remplace pas un test de charge représentatif.
- Les tests d'intégration démarrent l'application via TestClient ; ajouter une base de données et un environnement éphémère si le projet en utilise une.
- Les scans Trivy sont configurés pour échouer sur les vulnérabilités `CRITICAL`; ajuster la politique après analyse.
- Ajouter un registre de secrets, SBOM/CycloneDX, signature d'image (cosign), politiques OPA, approbation de production,
  sauvegardes, TLS/ALB, monitoring, alerting et stratégie de rollback avant production.
