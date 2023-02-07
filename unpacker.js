function unPack(code) {
    function indent(code) {
        try {
            var tabs = 0,
                old = -1,
                add = "";
            for (var i = 0; i < code.length; i++) {
                if (code[i].indexOf("{") != -1) tabs++;
                if (code[i].indexOf("}") != -1) tabs--;

                if (old != tabs) {
                    old = tabs;
                    add = "";
                    while (old > 0) {
                        add += "\t";
                        old--;
                    }
                    old = tabs;
                }

                code[i] = add + code[i];
            }
        } finally {
            tabs = null;
            old = null;
            add = null;
        }
        return code;
    }

    var env = {
        eval: function (c) {
            code = c;
        },
        window: {},
        document: {},
    };

    eval("with(env) {" + code + "}");

    code = (code + "")
        .replace(/;/g, ";\n")
        .replace(/{/g, "\n{\n")
        .replace(/}/g, "\n}\n")
        .replace(/\n;\n/g, ";\n")
        .replace(/\n\n/g, "\n");

    code = code.split("\n");
    code = indent(code);

    code = code.join("\n");
    return code;
    console.log(code);
}
code = "eval(function(p,a,c,k,e,d){e=function(c){return(c<a?'':e(parseInt(c/a)))+((c=c%a)>35?String.fromCharCode(c+29):c.toString(36))};if(!''.replace(/^/,String)){while(c--){d[e(c)]=k[c]||e(c)}k=[function(e){return d[e]}];e=function(){return'\\w+'};c=1};while(c--){if(k[c]){p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c])}}return p}('h o=\'1C://1B-1A.1z.1y.1x/1w/11/1v/1u/1t.1s\';h d=s.r(\'d\');h 0=B 1r(d,{\'1q\':{\'1p\':i},\'1o\':\'16:9\',\'D\':1,\'1n\':5,\'1m\':{\'1l\':\'1k\'},1j:[\'7-1i\',\'7\',\'1h\',\'1g\',\'1f-1e\',\'1d\',\'D\',\'1c\',\'1b\',\'1a\',\'19\',\'C\',\'18\'],\'C\':{\'17\':i}});8(!A.15()){d.14=o}x{j z={13:12,10:Z,Y:X,W:i,V:i};h c=B A(z);c.U(o);c.T(d);g.c=c}0.3("S",6=>{g.R.Q.P("O")});0.N=1;k v(b,n,m){8(b.y){b.y(n,m,M)}x 8(b.w){b.w(\'3\'+n,m)}}j 4=k(l){g.L.K(l,\'*\')};v(g,\'l\',k(e){j a=e.a;8(a===\'7\')0.7();8(a===\'f\')0.f();8(a===\'u\')0.u()});0.3(\'t\',6=>{4(\'t\')});0.3(\'7\',6=>{4(\'7\')});0.3(\'f\',6=>{4(\'f\')});0.3(\'J\',6=>{4(0.q);s.r(\'.I-H\').G=F(0.q.E(2))});0.3(\'p\',6=>{4(\'p\')});',62,101,'player|||on|sendMessage||event|play|if||data|element|hls|video||pause|window|const|true|var|function|message|eventHandler|eventName|source|ended|currentTime|querySelector|document|ready|stop|bindEvent|attachEvent|else|addEventListener|config|Hls|new|fullscreen|volume|toFixed|String|innerHTML|timestamp|ss|timeupdate|postMessage|parent|false|speed|landscape|lock|orientation|screen|enterfullscreen|attachMedia|loadSource|lowLatencyMode|enableWorker|Infinity|backBufferLength|600|maxMaxBufferLength||180|maxBufferLength|src|isSupported||iosNative|capture|airplay|pip|settings|captions|mute|time|current|progress|rewind|large|controls|kwik|key|storage|seekTime|ratio|global|keyboard|Plyr|m3u8|uwu|1f9f7f86da62151e6cfaa806f7b479c26ff71c78796f80a05165d5bae3c28c06|01|stream|org|nextcdn|cache|112|eu|https'.split('|'),0,{}))";
// code = `eval(function(p,a,c,k,e,d){e=function(c){return(c<a?'':e(parseInt(c/a)))+((c=c%a)>35?String.fromCharCode(c+29):c.toString(36))};if(!''.replace(/^/,String)){while(c--){d[e(c)]=k[c]||e(c)}k=[function(e){return d[e]}];e=function(){return'\\w+'};c=1};while(c--){if(k[c]){p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c])}}return p}('h o=\'1C://1B-1A.1z.1y.1x/1w/11/1v/1u/1t.1s\';h d=s.r(\'d\');h 0=B 1r(d,{\'1q\':{\'1p\':i},\'1o\':\'16:9\',\'D\':1,\'1n\':5,\'1m\':{\'1l\':\'1k\'},1j:[\'7-1i\',\'7\',\'1h\',\'1g\',\'1f-1e\',\'1d\',\'D\',\'1c\',\'1b\',\'1a\',\'19\',\'C\',\'18\'],\'C\':{\'17\':i}});8(!A.15()){d.14=o}x{j z={13:12,10:Z,Y:X,W:i,V:i};h c=B A(z);c.U(o);c.T(d);g.c=c}0.3("S",6=>{g.R.Q.P("O")});0.N=1;k v(b,n,m){8(b.y){b.y(n,m,M)}x 8(b.w){b.w(\'3\'+n,m)}}j 4=k(l){g.L.K(l,\'*\')};v(g,\'l\',k(e){j a=e.a;8(a===\'7\')0.7();8(a===\'f\')0.f();8(a===\'u\')0.u()});0.3(\'t\',6=>{4(\'t\')});0.3(\'7\',6=>{4(\'7\')});0.3(\'f\',6=>{4(\'f\')});0.3(\'J\',6=>{4(0.q);s.r(\'.I-H\').G=F(0.q.E(2))});0.3(\'p\',6=>{4(\'p\')});',62,101,'player|||on|sendMessage||event|play|if||data|element|hls|video||pause|window|const|true|var|function|message|eventHandler|eventName|source|ended|currentTime|querySelector|document|ready|stop|bindEvent|attachEvent|else|addEventListener|config|Hls|new|fullscreen|volume|toFixed|String|innerHTML|timestamp|ss|timeupdate|postMessage|parent|false|speed|landscape|lock|orientation|screen|enterfullscreen|attachMedia|loadSource|lowLatencyMode|enableWorker|Infinity|backBufferLength|600|maxMaxBufferLength||180|maxBufferLength|src|isSupported||iosNative|capture|airplay|pip|settings|captions|mute|time|current|progress|rewind|large|controls|kwik|key|storage|seekTime|ratio|global|keyboard|Plyr|m3u8|uwu|1f9f7f86da62151e6cfaa806f7b479c26ff71c78796f80a05165d5bae3c28c06|01|stream|org|nextcdn|cache|111|eu|https'.split('|'),0,{}))`;
unPack(code);
