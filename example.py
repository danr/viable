
from viable import serve, request, xmlesc

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
            <form
                onsubmit="set_query(this); refresh(); return false"
                noninput="set_query(this); refresh(); return false"
            >
    ''' + f'''
            {' '.join(map(str, range(5000)))}
                <input type=text name="jax" id="jax" value="{xmlesc(request.args.get('jax', ''))}" />
                <input type=text name="jox" id="jox" value="{xmlesc(request.args.get('jox', ''))}"
                />
                <button id=submit type=submit>heh</button>
                hmm
            </form>
            <pre>{xmlesc(str(request.args))}</pre>
            <pre>{xmlesc(str(path))}</pre>
            {' '.join(map(str, range(5000)))}
    '''
