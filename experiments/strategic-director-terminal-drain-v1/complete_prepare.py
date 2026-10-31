"""Complete the preserved CPU-only preparation failure; no native tree writes."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=HERE/'candidate/client/Client.cpp'
text=p.read_text()
assert 'NativeRequestTermination pending_ids=' not in text
text=text.replace('#include "StdInc.h"','#include "StdInc.h"\n#include <sstream>\n#include "../lib/serializer/CTypeList.h"',1)
old='DirectorNativeRequestRegistered id=%u player=%d type=%s",requestID,player.getNum(),typeid(request).name()'
new='DirectorNativeRequestRegistered id=%u player=%d pack_type=%d type=%s",requestID,player.getNum(),CTypeList::getInstance().getTypeID(&request),typeid(request).name()'
assert text.count(old)==1
text=text.replace(old,new)
old='\twaitingRequest.requestTermination();'
assert text.count(old)==1
text=text.replace(old,'''\tconst auto remaining=waitingRequest.snapshot();
\tstd::ostringstream ids;ids << '[';
\tfor(size_t i=0;i<remaining.size();++i) { if(i) ids << ',';ids << remaining[i]; }
\tids << ']';
\tlogGlobal->info("NativeRequestTermination pending_ids=%s",ids.str());
'''+old)
p.write_text(text)
script=(HERE/'prepare.py').read_text()
header=script[:script.index('for relative in entries:')]
tail=script[script.index("p=HERE/'candidate/client/NetPacksClient.cpp'"):]
tail=tail.replace('if (!cl.waitingRequest.tryRemovingElement(pack.requestID))','if(!cl.waitingRequest.tryRemovingElement(pack.requestID))')
tail=tail.replace("text=text.replace(needle,'''", "text=text.replace(needle,'''\tlogAi->info(\"NativeRequestAck id=%u player=%d pack_type=%d success=%d\",pack.requestID,pack.player.getNum(),pack.packType,pack.result);\n",1)
exec(compile(header+tail,str(HERE/'prepare.py')+'-completion','exec'),{'__file__':str(HERE/'prepare.py')})
