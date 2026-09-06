# Migration Agent Lab

OSB → MuleSoft migration sürecini kullanarak Python orkestrasyonu ve AI agent yapısını öğrenme projesi.

## Başlangıç

VS Code terminalinde, Python 3.11 veya üzeri kurulu olduğunda:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe run_agent.py INT-101
```

İlk çalıştırma örnek görevi okur ve `workspace/INT-101/run-status.json` dosyasını oluşturur. Henüz AI çağrısı, OSB analizi veya MuleSoft kod üretimi yapmaz.

## Klasörler

- `orchestrator/`: Python akış yönetimi.
- `samples/INT-101/`: Örnek görev ve ileride eklenecek OSB dosyaları.
- `mule-projects/`: MuleSoft projeleri; Mule eklentisiyle burada oluşturulacak.
- `workspace/`: Çalıştırma çıktıları; Git'e eklenmez.

## İlk hedef

1. Örnek OSB dosyalarını ekle.
2. Model sağlayıcısını seç ve ilk API çağrısını yap.
3. Dosyalara dayanan, eksik bilgileri açıkça belirten analiz çıktısı üret.
4. Çıktının yapısını doğrula ve kaydet.

Sonraki aşamalar: Jira bağlantısı, MuleSoft kod üretimi, test ve sınırlı düzeltme döngüsü, draft PR.

API anahtarlarını kaynak koda yazma. Model bağlantısı eklendiğinde ortam değişkenleri kullanılacak.

## GitHub ve Jira bağlantıları

GitHub: https://github.com/okancalisir/migrationlab

Jira: https://teamdefinex.atlassian.net

`.env.example` dosyasını `.env` olarak kopyala. `JIRA_EMAIL` alanına Atlassian hesap e-postanı, `JIRA_API_TOKEN` alanına API token'ını yerel editörde gir. Token'ı sohbetten gönderme. `.env` Git dışında tutulur.

Token oluşturma: https://id.atlassian.com/manage-profile/security/api-tokens

Kapsamlı (scoped) token kullanıyorsan `JIRA_CLOUD_ID` alanını da doldur. Client bu durumda `api.atlassian.com/ex/jira/{cloudId}` adresini kullanır. Cloud ID, giriş yaptığın tarayıcıda https://teamdefinex.atlassian.net/_edge/tenant_info adresinden öğrenilebilir. Token kapsamları kullanılan kullanıcı ve iş okuma uçlarını desteklemeli; hesabın da ilgili işe erişimi olmalı.

Resmi kimlik doğrulama açıklaması: https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/

```powershell
.\.venv\Scripts\python.exe check_connections.py all
.\.venv\Scripts\python.exe run_agent.py MIG-1 --source jira
```

`MIG-1` yerine Jira'da mevcut olan iş anahtarını kullan. Jira bağlantısı şu an kimlik doğrulama kontrolü, görev açıklaması ve ek dosyaların metadata bilgisini okur. Ek dosyaları henüz indirmez; açıklamayı Jira'nın ADF JSON biçiminde saklar. Jira'ya yazma ve AI analizi henüz yoktur.

GitHub kontrolü yalnızca okuma erişimini doğrular. Commit/push işlemleri Git üzerinden yapılır; otomatik PR oluşturma henüz eklenmedi.
