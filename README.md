# Migration Agent Lab

OSB → MuleSoft migration sürecini kullanarak Python orkestrasyonu ve AI agent yapısını öğrenme projesi.

## Başlangıç

VS Code terminalinde, Python 3.11 veya üzeri kurulu olduğunda:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe run_agent.py INT-101
```

İlk çalıştırma örnek görevi okur ve `workspace/INT-101/run-status.json` dosyasını oluşturur.

## Klasörler

- `orchestrator/`: Python akış yönetimi.
- `samples/INT-101/`: Örnek görev ve ileride eklenecek OSB dosyaları.
- `mule-projects/`: MuleSoft projeleri; Mule eklentisiyle burada oluşturulacak.
- `workspace/`: Çalıştırma çıktıları; Git'e eklenmez.

## Analysis Agent

Agent Jira görevini okur; WSDL, XSD, proxy, business service, pipeline ve XQuery gibi metin eklerini indirir. Verilen servis için kanıtlı OSB analizi ve MuleSoft teknik tasarımı üretir. Kaynakta bulunmayan endpoint, timeout veya authentication değerlerini uydurmaz.

Sonraki aşamalar: Jira bağlantısı, MuleSoft kod üretimi, test ve sınırlı düzeltme döngüsü, draft PR.

API anahtarlarını kaynak koda yazma. Jira ve OpenAI anahtarları yalnızca `.env` dosyasında tutulur.

## GitHub ve Jira bağlantıları

GitHub: https://github.com/okancalisir/migrationlab

Jira: https://teamdefinex.atlassian.net

`.env.example` dosyasını `.env` olarak kopyala. `JIRA_EMAIL` alanına Atlassian hesap e-postanı, `JIRA_API_TOKEN` alanına API token'ını yerel editörde gir. Token'ı sohbetten gönderme. `.env` Git dışında tutulur.

Token oluşturma: https://id.atlassian.com/manage-profile/security/api-tokens

Kapsamlı (scoped) token kullanıyorsan `JIRA_CLOUD_ID` alanını da doldur. Client bu durumda `api.atlassian.com/ex/jira/{cloudId}` adresini kullanır. Cloud ID, giriş yaptığın tarayıcıda https://teamdefinex.atlassian.net/_edge/tenant_info adresinden öğrenilebilir. Token kapsamları kullanılan kullanıcı ve iş okuma uçlarını desteklemeli; hesabın da ilgili işe erişimi olmalı.

Resmi kimlik doğrulama açıklaması: https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe check_connections.py all
.\.venv\Scripts\python.exe run_agent.py KAN-1 --source jira --service CustomerLookup --analyze
```

`KAN-1` yerine Jira'daki gerçek iş anahtarını, `CustomerLookup` yerine analiz edilecek OSB servisinin adını kullan.

Üretilen dosyalar:

- `workspace/KAN-1/jira/task.json`
- `workspace/KAN-1/jira/attachments/`
- `workspace/KAN-1/analysis/requirement-analysis.json`
- `workspace/KAN-1/analysis/osb-analysis.json`
- `workspace/KAN-1/analysis/analysis.md`
- `workspace/KAN-1/design/mule-design.json`
- `workspace/KAN-1/design/technical-design.md`

İlk sürüm yalnızca analiz ve tasarım üretir. MuleSoft XML/RAML/DataWeave kod üretimi sonraki aşamadır.

GitHub kontrolü yalnızca okuma erişimini doğrular. Commit/push işlemleri Git üzerinden yapılır; otomatik PR oluşturma henüz eklenmedi.
