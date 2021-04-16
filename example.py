
from viable import serve, request, esc

@serve
def SimpleFlaskHMR(path='/'):
    return '''
        <style>
            body {
                width: 900px;
                margin: 5px auto;
                font-family: sans;
            }
        </style>
    ''' + f'''
        {' '.join(map(str, range(1000)))}
        <pre>{esc(str(request.args))}</pre>
        <pre>{esc(str(path))}</pre>
        <form
            onsubmit="set_query(this); refresh(); return false"
            onchange="set_query(this); refresh(); return false"
            noninput="set_query(this); refresh(); return false"
        >
            <input type=text name="jax" id="jax" value="{esc(request.args.get('jax', ''))}" />
            <input type=text name="jox" id="jox" value="{esc(request.args.get('jox', ''))}" />
            <button id=submit type=submit>heh</button>
        </form>
        {' '.join(map(str, range(1000)))}
    '''


