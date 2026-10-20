"""Static VBA release checks. Does not compile or run Excel/VBA."""
from pathlib import Path
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent


def check(sources=None):
    manifest = json.loads((HERE / 'manifest.json').read_text())
    checked = 0
    for row in manifest['files']:
        if sources:
            path = Path(sources[row['workbook']]) / row['file']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row['after_sha256'], f'Changed since manifest: {path}'
            checked += 1
    for path in [HERE/'common/ExcelSetupSync.bas',HERE/'rv80/ExcelSetupRV80.bas',HERE/'sigpc/ExcelSetupSIGPC.bas']:
        text = path.read_text(encoding='utf-8-sig')
        assert text.startswith('Attribute VB_Name = "'), path
        assert 'Option Explicit' in text
        names = re.findall(r'(?im)^(?:Public|Private) (?:Sub|Function) (\w+)',text)
        assert len(names) == len(set(n.lower() for n in names)), f'Duplicate procedure: {path}'
        assert len(re.findall(r'(?im)^End (?:Sub|Function)\s*$',text)) == len(names), path
        assert max(map(len,text.splitlines())) < 1024, f'VBA physical line too long: {path}'
        assert not re.search(r'(?i)token [a-z0-9]{10,}:',text), 'Literal API credential'
    assert "ACN.AC_RequireSession()" in (HERE/'common/ExcelSetupSync.bas').read_text()
    if sources:
        assert (Path(sources['rv80'])/'ExcelSetupSync.bas').read_bytes() == (Path(sources['sigpc'])/'ExcelSetupSync.bas').read_bytes()
        assert (Path(sources['rv80'])/'ExcelSetupSync.bas').read_bytes() == (HERE/'common/ExcelSetupSync.bas').read_bytes()
        for key, folder in sources.items():
            for filename in ('ACN.bas', 'ExcelSetupSync.bas', 'ExcelSetupRV80.bas' if key=='rv80' else 'ExcelSetupSIGPC.bas'):
                assert (Path(folder)/filename).is_file()
        pc=(Path(sources['sigpc'])/'MappingPipeline.bas').read_text(encoding='utf-8-sig')
        assert 'MP_ErpTagsRowInScope(ws, r, ctx)' in pc
        assert 'ESHost_CucMap(mESRunPo' in pc
        ab=(Path(sources['sigpc'])/'AsBuiltCycle.bas').read_text(encoding='utf-8-sig')
        assert 'ESHost_MaterialLinks sourcePo, sourceUnit' in ab
        rv=(Path(sources['rv80'])/'ItemCatalogueSync.bas').read_text(encoding='utf-8-sig')
        assert 'ESHost_FamilyForPo' not in rv, 'Do not replace existing Project catalogue authority'
    return {'status':'PASS','manifest_files_checked':checked,'new_modules_checked':3,'VBA_Compile':'NOT TESTED'}


if __name__ == '__main__':
    sources={'rv80':sys.argv[1],'sigpc':sys.argv[2]} if len(sys.argv)==3 else None
    print(json.dumps(check(sources),indent=2))
