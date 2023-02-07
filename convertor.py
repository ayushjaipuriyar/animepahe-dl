def unPack(code):
    def indent(code):
        tabs = 0
        old = -1
        add = ""
        for i in range(len(code)):
            if "{" in code[i]:
                tabs += 1
            if "}" in code[i]:
                tabs -= 1

            if old != tabs:
                old = tabs
                add = ""
                while old > 0:
                    add += "\t"
                    old -= 1
                old = tabs

            code[i] = add + code[i]

        return code

    env = {
        "eval": (lambda c: (nonlocal code
                            code := c)),
        "window": {},
        "document": {},
    }

    exec(f"with env: {code}", env)
    code = (str(code)
            .replace(";", ";\n")
            .replace("{", "\n{\n")
            .replace("}", "\n}\n")
            .replace("\n;\n", ";\n")
            .replace("\n\n", "\n"))

    code = code.split("\n")
    code = indent(code)

    code = "\n".join(code)
    return code


code = "eval(function(p,a,c,k,e,d){e=function(c){return(c<a?'':e(parseInt(c/a)))+((c=c%a)>35?String.fromCharCode(c+29):c.toString(36))};if(!''.replace(/^/,String)){while(c--){d[e(c)]=k[c]||e(c)}k=[function(e){return d[e]}];e=function(){return'\\w+'};c=1};while(c--){if(k[c]){p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c])}}return p}('h o=\'1C://1B-1A.1z.1y.1x/1w/1v/1u/1t/1s.1r\';h d=s.r(\'d\');h 0=B 1q(d,{\'1p\':{\'1o\':i},\'1n\':\'16:9\',\'D\':1,\'1m\':5,\'1l\':{\'1k\':\'1j\'},1i:[\'7-1h\',\'7\',\'1g\',\'1f\',\'1e-1d\',\'1c\',\'D\',\'1b\',\'1a\',\'19\',\'18\',\'C\',\'17\'],\'C\':{\'15\':i}});8(!A.14()){d.13=o}x{j z={12:11,10:Z,Y:X,W:i,V:i};h c=B A(z);c.U(o);c.T(d);g.c=c}0.3("S",6=>{g.R.Q.P("O")});0.N=1;k v(b,n,m){8(b.y){b.y(n,m,M)}x 8(b.w){b.w(\'3\'+n,m)}}j 4=k(l){g.L.K(l,\'*\')};v(g,\'l\',k(e){j a=e.a;8(a===\'7\')0.7();8(a===\'f\')0.f();8(a===\'u\')0.u()});0.3(\'t\',6=>{4(\'t\')});0.3(\'7\',6=>{4(\'7\')});0.3(\'f\',6=>{4(\'f\')});0.3(\'J\',6=>{4(0.q);s.r(\'.I-H\').G=F(0.q.E(2))});0.3(\'p\',6=>{4(\'p\')});',62,101,'player|||on|sendMessage||event|play|if||data|element|hls|video||pause|window|const|true|var|function|message|eventHandler|eventName|source|ended|currentTime|querySelector|document|ready|stop|bindEvent|attachEvent|else|addEventListener|config|Hls|new|fullscreen|volume|toFixed|String|innerHTML|timestamp|ss|timeupdate|postMessage|parent|false|speed|landscape|lock|orientation|screen|enterfullscreen|attachMedia|loadSource|lowLatencyMode|enableWorker|Infinity|backBufferLength|600|maxMaxBufferLength|180|maxBufferLength|src|isSupported|iosNative||capture|airplay|pip|settings|captions|mute|time|current|progress|rewind|large|controls|kwik|key|storage|seekTime|ratio|global|keyboard|Plyr|m3u8|uwu|77782ced01478044c1cfd76f7818acd7066b88031a18940267022e3fbf9b1509|02|99|stream|org|nextcdn|files|994|eu|https'.split('|'),0,{}))"
print(unPack(code))
