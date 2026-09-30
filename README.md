# شكاوي ومقترحات مراكز الشباب

مشروع Django مستقل محليًا. الصفحتان `/ar/` و`/en/` تستقبلان الشكاوي والمقترحات بالعربية الفصحى وEnglish. لوحة الموظفين `/staff/` تعرض الطلبات وتسمح بتغيير حالتها.

## البيانات والربط

- المشروع يقرأ المراكز النشطة والعملاء من Database الخاصة بـ EZYXS فقط.
- الوضع المحلي الافتراضي يقرأ `../ezyxs-backend/db.sqlite3` عبر اتصال SQLite للقراءة فقط.
- إذا لم تحتوِ قاعدة EZYXS المحلية على مراكز، يستخدم المشروع قائمة محفوظة للمراكز السبعة التي أرجعتها `https://moys-test.ezyxs.com/ar/api/v3/facilities/` في 30 سبتمبر 2026. القائمة نسخة ثابتة وقد تحتاج تحديثًا لاحقًا.
- الشكاوي والمقترحات تُحفظ في `feedback.sqlite3` داخل هذا المشروع.
- لكل طلب نسخة من اسم المركز ورقم الهاتف وقت الإرسال. إذا وجدنا العميل في قاعدة EZYXS، نحفظ أيضًا رقمه المرجعي واسمه وبريده.
- قبول رقم الهاتف وحده مؤقتًا مسموح به. لوحة الموظفين تميز الطلب الذي طابق عميل EZYXS من الطلب الذي يحتوي على رقم هاتف فقط.
- رقم الهاتف يُستخدم لمحاولة مطابقة العميل، لكنه لا يثبت أن مُرسل الطلب يمتلك الرقم. هذه النسخة لا ترسل OTP بناءً على المتطلب الحالي.
- لوحة الموظفين لها مستخدمون محليون في هذا المشروع؛ حسابات موظفي EZYXS غير موصولة بها حتى الآن.

## التشغيل المحلي

من مجلد المشروع في PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8010
```

`migrate` ينشئ جداول المشروع الجديد في `feedback.sqlite3` فقط. أمر `createsuperuser` ينشئ حسابًا محليًا للموظف الذي سيدخل `/staff/`. الصفحتان بعد التشغيل:

- `http://127.0.0.1:8010/ar/` للإرسال بالعربية.
- `http://127.0.0.1:8010/en/` للإرسال بالإنجليزية.
- `http://127.0.0.1:8010/staff/` للموظفين.

لو Database المحلية بتاعة EZYXS في مكان مختلف، اضبط `EZYXS_SQLITE_PATH` لمسارها المطلق قبل التشغيل.

## ربط MySQL لاحقًا

اضبط `EZYXS_DB_ENGINE=mysql` والمتغيرات `EZYXS_DB_NAME`, `EZYXS_DB_USER`, `EZYXS_DB_PASSWORD`, `EZYXS_DB_HOST`, `EZYXS_DB_PORT`. حساب MySQL الخاص بهذا المشروع يجب أن يكون له `SELECT` فقط على `facility_facility`, `accounts_customerprofile`, `accounts_customuser`.

قبل النشر، اضبط `FEEDBACK_DEBUG=false`، و`FEEDBACK_SECRET_KEY` بقيمة سرية، و`FEEDBACK_ALLOWED_HOSTS` باسم الموقع. قاعدة بيانات الشكاوي المحلية تحتاج خطة نقل إلى MySQL أو PostgreSQL إذا استخدمت أكثر من Server.

## ملفات مهمة

- `config/settings.py`: إعدادات Django واتصالي قواعد البيانات.
- `feedback/services.py`: قراءة مراكز الشباب والعملاء من EZYXS.
- `feedback/data/moys_test_facilities.json`: نسخة المراكز التي قرأناها من بيئة التجربة.
- `feedback/texts.py`: نصوص الصفحتين العربية والإنجليزية.
- `feedback/forms.py`: التحقق من مدخلات نموذج الإرسال.
- `feedback/models.py`: شكل الطلب المخزن محليًا.
- `feedback/views.py`: استقبال النموذج وإرجاع صفحة التأكيد.
- `feedback/admin.py`: عرض الطلبات وصلاحيات تغيير الحالة للموظفين.
