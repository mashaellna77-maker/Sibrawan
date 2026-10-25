"""No secrets in URLs, exceptions, logs or returned status objects."""
from pathlib import Path
import hashlib
import json
import time
import re
import requests
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parent
_state={'status':'not_tested','detail':'لم يُختبر الاتصال بعد.'}
_fingerprint=None

def _event(model, attempt, started, response=None, exception=None):
    """Allowlisted diagnostics only: never log prompts, headers or credentials."""
    key,_=settings()
    error={}
    if response is not None:
        try: error=response.json().get('error',{})
        except (ValueError,AttributeError): pass
    if not isinstance(error,dict): error={}
    event={'checked_at':time.time(),'model':model,'attempt':attempt,
           'elapsed_seconds':round(time.monotonic()-started,2),
           'http_code':response.status_code if response is not None and isinstance(response.status_code,int) else None,
           'error_type':type(exception).__name__ if exception else error.get('status'),
           'message':str(error.get('message',''))[:1200]}
    if key: event['message']=event['message'].replace(key,'[محجوب]')
    try:
        (ROOT/'.runtime').mkdir(exist_ok=True)
        with (ROOT/'.runtime/gemini-events.jsonl').open('a',encoding='utf-8') as log:
            log.write(json.dumps(event,ensure_ascii=False)+'\n')
    except OSError: pass
    return event

def _post_with_retry(url, headers, payload, model):
    # Two attempts total. Permanent request/auth/model/quota failures are not retried.
    for attempt in (1,2):
        started=time.monotonic()
        try:
            response=requests.post(url,headers=headers,json=payload,timeout=(10,60))
            event=_event(model,attempt,started,response=response)
            if response.status_code in (500,502,503,504) and attempt==1:
                time.sleep(1)
                continue
            return response,event
        except (requests.Timeout,requests.ConnectionError) as exc:
            _event(model,attempt,started,exception=exc)
            if attempt==2: raise
            time.sleep(1)

def settings():
    config=dotenv_values(ROOT/'.env')
    return (config.get('GEMINI_API_KEY') or '').strip(),(config.get('GEMINI_MODEL') or 'gemini-3.8-flash').strip().removeprefix('models/')

def connection_state():
    global _fingerprint,_state
    key,model=settings()
    fingerprint=hashlib.sha256((key+'|'+model).encode()).digest()
    if _fingerprint!=fingerprint:
        _fingerprint=fingerprint
        _state={'status':'not_tested' if key else 'missing_key',
                'detail':'المفتاح موجود؛ لم ينجح اختبار اتصال بعد.' if key else 'أضف المفتاح محليًا في .env لتفعيل Gemini؛ رصد المحلي متاح.'}
        try:
            saved=json.loads((ROOT/'.runtime/connection.json').read_text(encoding='utf-8'))
            if key and saved.get('fingerprint')==fingerprint.hex() and time.time()-saved.get('checked_at',0)<86400:
                _state={k:saved[k] for k in ['status','detail','checked_at']}
        except (OSError,ValueError,KeyError,TypeError): pass
    try:
        saved=json.loads((ROOT/'.runtime/connection.json').read_text(encoding='utf-8'))
        if key and saved.get('fingerprint')==fingerprint.hex() and time.time()-saved.get('checked_at',0)<86400 and saved.get('checked_at',0)>_state.get('checked_at',0):
            _state={k:saved[k] for k in ['status','detail','checked_at']}
    except (OSError,ValueError,KeyError,TypeError): pass
    return {**_state,'key_present':bool(key),'model':model}

def _record(status,detail):
    connection_state()
    _state.update(status=status,detail=detail)
    _state['checked_at']=time.time()
    try:
        (ROOT/'.runtime').mkdir(exist_ok=True)
        (ROOT/'.runtime/connection.json').write_text(json.dumps({**_state,'fingerprint':_fingerprint.hex()}),encoding='utf-8')
    except OSError: pass
    return {'ok':status=='connected','status':status,'detail':detail}

def _error(code):
    if code in (401,403): return _record('authentication','تعذر تفويض Gemini. راجع المفتاح وصلاحياته ومشروع Google محليًا.')
    if code==429: return _record('quota','حصة Gemini أو حد الطلبات غير متاح حاليًا. تحقق من الحصة والفوترة في Google AI Studio.')
    if code==404: return _record('model','النموذج المحدد غير متاح. راجع GEMINI_MODEL في .env وصلاحية النموذج لحسابك.')
    if code==400: return _record('request','رفض Gemini إعداد الطلب أو المفتاح. راجع إعدادات النموذج والمفتاح محليًا.')
    if code>=500: return _record('service','خدمة Gemini غير متاحة مؤقتًا؛ جرّب لاحقًا.')
    return _record('request','تعذر إتمام طلب Gemini؛ استخدم رد رصد المحلي.')

def generate(question,system,max_tokens=1600,verify_model=False):
    state=connection_state(); key,model=settings()
    if not key: return {**_record('missing_key',state['detail']),'text':''}
    if not re.fullmatch(r'[A-Za-z0-9._-]+',model):
        return {**_record('model','اسم GEMINI_MODEL غير صالح؛ لا تستخدم رابطًا أو مسارًا.'),'text':''}
    headers={'x-goog-api-key':key,'Content-Type':'application/json'}
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}'
    generation={'temperature':0.2,'maxOutputTokens':max_tokens}
    if model.startswith('gemini-3.8-flash'):
        generation['thinkingConfig']={'thinkingLevel':'low'}
    try:
        if verify_model:
            metadata=requests.get('https://generativelanguage.googleapis.com/v1beta/models',headers=headers,params={'pageSize':1000},timeout=(10,20))
            if not metadata.ok: return {**_error(metadata.status_code),'text':''}
            available=metadata.json().get('models',[])
            if not any(m.get('name')=='models/'+model and 'generateContent' in m.get('supportedGenerationMethods',[]) for m in available):
                return {**_record('model','النموذج المحدد لا يظهر كنموذج توليد نص متاح للحساب.'),'text':''}
        response,event=_post_with_retry(url+':generateContent',headers,
            {'system_instruction':{'parts':[{'text':system}]},
                  'contents':[{'role':'user','parts':[{'text':question[:3000]}]}],
                  'generationConfig':generation},model)
        if not response.ok:
            result=_error(response.status_code)
            result['detail']+=f" (HTTP {response.status_code}؛ {event['error_type'] or 'HTTPError'}؛ المحاولات: {event['attempt']})"
            return {**result,'text':'','diagnostic':event}
        body=response.json()
        candidates=body.get('candidates') or []
        parts=candidates[0].get('content',{}).get('parts',[]) if candidates else []
        text='\n'.join(p.get('text','') for p in parts if not p.get('thought')).strip()
        if not text:
            return {**_record('empty','استجابت الخدمة دون نص قابل للعرض. سيُستخدم رصد المحلي.'),'text':''}
        return {**_record('connected','نجح اتصال Gemini وإنتاج رد نصي.'),'text':text.replace(key,'[محجوب]')}
    except requests.Timeout as exc:
        return {**_record('timeout',f'انتهت مهلة Gemini ({type(exc).__name__}) بعد محاولتين كحد أقصى؛ لا توجد استجابة HTTP. سيُستخدم رصد المحلي.'),'text':''}
    except requests.RequestException:
        return {**_record('network','تعذر الوصول إلى Gemini عبر الشبكة. سيُستخدم رصد المحلي.'),'text':''}
    except (ValueError,KeyError,TypeError):
        return {**_record('response','تعذر قراءة رد Gemini بأمان؛ سيُستخدم رصد المحلي.'),'text':''}

def probe():
    return generate('ما اسمك؟ أجب بجملة عربية واحدة دون أرقام.',
                    'اسمك رصد 📡، مساعد سِبرَوان | Sibrawan. أجب بالعربية باختصار.',
                    max_tokens=512,verify_model=True)
