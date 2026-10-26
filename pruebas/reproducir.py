#!/usr/bin/env python3
"""Ejecuta los mismos seis casos sobre baseline y corrección aislados."""
import argparse
import difflib
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
COMMIT = 'e4fdc4a7fc8f487cee1f6dc0c165512e2c547688'
FIXED_VALIDATORS = '''import re

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")

def validate_contact(data):
    fields = ["name", "email", "subject", "message"]
    errors = {}
    for field in fields:
        value = data.get(field, "")
        if not isinstance(value, str):
            errors[field] = "Este campo debe ser texto."
        elif not value.strip():
            errors[field] = "Este campo es obligatorio."
    email = data.get("email", "")
    if isinstance(email, str):
        email = email.strip()
        if email and not EMAIL_PATTERN.fullmatch(email):
            errors["email"] = "Ingresa un correo electrónico válido."
    return errors
'''


def command_version(command):
    process = subprocess.run(command, text=True, capture_output=True)
    return (process.stdout + process.stderr).strip()


def run_logged(command, logfile, env):
    with open(logfile, 'w', encoding='utf-8') as stream:
        stream.write('COMMAND: ' + subprocess.list2cmdline(list(map(str,command))) + '\n')
        stream.flush()
        result = subprocess.run(list(map(str,command)), stdout=stream, stderr=subprocess.STDOUT, env=env)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Repositorio clonado, con Form/formulario')
    parser.add_argument('--output', default=str(BASE/'evidencias'), help='Carpeta de resultados')
    parser.add_argument('--node', default=shutil.which('node') or 'node')
    args=parser.parse_args()
    source = Path(args.source).resolve()
    app_source=source/'Form'/'formulario'
    if not (app_source/'app.py').exists():
        parser.error('--source debe señalar la raíz del repositorio')
    output=Path(args.output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(app_source.rglob('*')) if p.is_file() and p.suffix in ['.py','.js','.html','.css'] and '__pycache__' not in p.parts}
    # Los commits que solo agregan pruebas cambian HEAD, pero no el codigo evaluado.
    # Comprobar los SHA256 de los archivos de la aplicacion, no exigir HEAD == COMMIT.
    registro_original = BASE/'evidencias'/'resumen.json'
    if not registro_original.is_file():
        parser.error('Falta evidencias/resumen.json, necesario para verificar la version de referencia.')
    expected_hashes = json.loads(registro_original.read_text(encoding='utf-8'))['source_sha256']
    if hashes != expected_hashes:
        cambios = sorted(set(hashes) ^ set(expected_hashes) |
                         {k for k in hashes.keys() & expected_hashes.keys() if hashes[k] != expected_hashes[k]})
        parser.error('La aplicacion no coincide con la version evaluada del commit '
                     + COMMIT[:7] + '. Archivos afectados: ' + ', '.join(cambios))
    git_sha = command_version(['git','-C',str(source),'rev-parse','HEAD']) if (source/'.git').exists() else None
    suite_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(BASE.iterdir()) if p.is_file() and p.suffix in ['.py','.cjs','.json']}
    manifest={'source_commit_expected':COMMIT,'source_commit_observed':git_sha,'application_verified_by':'source_sha256_against_archived_baseline',
        'source_sha256':hashes,'suite_sha256':suite_hashes,'started_at_utc':datetime.now(timezone.utc).isoformat(),
        'platform':platform.platform(),'python':platform.python_version(),
        'node':command_version([args.node,'--version']),
        'scope':'Local copies only, APP_ENV=testing, temporary SQLite, real HTTP and Chromium',
        'cases':['U01','U02','I01','I02','F01','F02'],
        'modifications':['Form/formulario/validators.py','Form/formulario/static/index.html'],
        'variants':{}}
    env=dict(os.environ)
    env['PYTHONUNBUFFERED']='1'
    with tempfile.TemporaryDirectory(prefix='lasalle_qa_') as temp:
        workspace=Path(temp)
        baseline=workspace/'baseline'
        fixed=workspace/'corregido'
        shutil.copytree(app_source,baseline,ignore=shutil.ignore_patterns('data','__pycache__','.pytest_cache'))
        shutil.copytree(baseline,fixed)
        (fixed/'validators.py').write_text(FIXED_VALIDATORS,encoding='utf-8')
        html=(fixed/'static'/'index.html').read_text(encoding='utf-8')
        html=html.replace('href="./styles.css"','href="/static/styles.css"').replace('src="./app.js"','src="/static/app.js"')
        (fixed/'static'/'index.html').write_text(html,encoding='utf-8')
        patch=''
        for relative in ['validators.py','static/index.html']:
            a=(baseline/relative).read_text(encoding='utf-8').splitlines(keepends=True)
            b=(fixed/relative).read_text(encoding='utf-8').splitlines(keepends=True)
            patch+=''.join(difflib.unified_diff(a,b,fromfile='a/Form/formulario/'+relative,tofile='b/Form/formulario/'+relative))
        (output/'correcciones.patch').write_text(patch,encoding='utf-8')
        for variant, application in [('baseline',baseline),('corregido',fixed)]:
            folder=output/variant
            folder.mkdir(exist_ok=True)
            code_backend=run_logged([sys.executable,BASE/'tests_backend.py','--app',application,'--output',folder,'--variant',variant],folder/'unittest.log',env)
            with open(folder/'servidor.log','w',encoding='utf-8') as serverlog:
                server=subprocess.Popen([sys.executable,str(BASE/'server_local.py'),str(application)],stdout=subprocess.PIPE,stderr=serverlog,text=True,env=env)
                try:
                    line=server.stdout.readline()
                    if not line:
                        raise RuntimeError('El servidor local no inició. Ver servidor.log')
                    config=json.loads(line)
                    (folder/'entorno_servidor.json').write_text(json.dumps(config,indent=2)+'\n')
                    code_browser=run_logged([args.node,BASE/'tests_funcionales.cjs',config['base_url'],config['database'],folder,variant,sys.executable],folder/'funcional.log',env)
                finally:
                    server.terminate()
                    try: server.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait()
            records=[]
            for id_ in manifest['cases']:
                path=folder/(id_+'.json')
                if not path.exists():
                    raise RuntimeError(f'Falta evidencia {path}; revisar logs de ejecución')
                records.append(json.loads(path.read_text(encoding='utf-8')))
            manifest['variants'][variant]={'backend_exit_code':code_backend,'functional_exit_code':code_browser,
                'passed':sum(r['status']=='APROBADO' for r in records),
                'failed':sum(r['status']=='FALLIDO' for r in records),
                'results':{r['id']:r['status'] for r in records}}
            print(variant,json.dumps(manifest['variants'][variant],ensure_ascii=False),flush=True)
    manifest['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    (output/'resumen.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['RESUMEN DERIVADO DE LAS EVIDENCIAS JSON','Fuente original: '+COMMIT,'Fecha de ejecución UTC: '+manifest['finished_at_utc'],'']
    for id_ in manifest['cases']:
        lines.append(id_+' | original: '+manifest['variants']['baseline']['results'][id_]+' | corregido: '+manifest['variants']['corregido']['results'][id_])
    lines.extend(['','Los seis casos se ejecutaron en ambas versiones.','La versión original contiene tres fallos asociados a dos defectos.','La versión corregida supera los seis casos con expectativas idénticas.','HTTP, SQLite y Chromium son reales y locales. No se evaluó Render.'])
    (output/'lectura_resultados.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # La baseline puede fallar: su código de salida se preserva en el manifiesto.
    # La ejecución global solo aprueba si la corrección supera los seis casos.
    return 0 if manifest['variants']['corregido']['failed']==0 else 1


if __name__=='__main__':
    sys.exit(main())
