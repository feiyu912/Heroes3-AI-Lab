import json
from pathlib import Path
import matplotlib.pyplot as plt

r=Path(__file__).parent
data=json.loads((r/'CHALLENGE_RESULTS.json').read_text())
rows={x['name']:x for x in data['fresh_results']}
plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
fig,axes=plt.subplots(1,2,figsize=(12,5.5),gridspec_kw={'width_ratios':[3,2]})
groups=[(['fresh-v3-vs-battleai','fresh-upstream-vs-battleai','fresh-selected-vs-battleai'],
         ['原模型','作者原版','当前选定模型'],'对 BattleAI'),
        (['fresh-v3-vs-upstream','fresh-selected-vs-upstream'],['原模型','当前选定模型'],'直接对战作者模型')]
for ax,(names,labels,title) in zip(axes,groups):
    values=[rows[n]['summary'][0]['win_rate']*100 for n in names]
    errors=[[v-rows[n]['scenario_cluster95'][0]*100 for n,v in zip(names,values)],
            [rows[n]['scenario_cluster95'][1]*100-v for n,v in zip(names,values)]]
    colors=['#8495a7','#e7a448','#287b77'] if len(names)==3 else ['#8495a7','#287b77']
    ax.bar(labels,values,color=colors,width=.58,yerr=errors,capsize=5,error_kw={'elinewidth':1.4})
    for i,(n,value) in enumerate(zip(names,values)):
        top=rows[n]['scenario_cluster95'][1]*100
        ax.text(i,min(104,top+2),f'{value:.1f}%',ha='center',fontsize=12,fontweight='bold')
    ax.axhline(50,color='#61717b',linestyle='--',linewidth=1)
    ax.set_ylim(0,110);ax.set_yticks([0,25,50,75,100]);ax.set_title(title,fontsize=14,pad=12)
    ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    ax.spines[['top','right']].set_visible(False)
axes[0].axhline(95,color='#b75b51',linestyle=':',linewidth=1.4,label='本轮接近100%目标：95%')
axes[0].legend(loc='upper left',fontsize=9,frameon=False)
axes[0].set_ylabel('真实胜率（%）')
fig.suptitle('新场景共同基准：兵力与部署完全镜像',fontsize=17,fontweight='bold',y=.98)
fig.text(.5,.025,'每项512场；超时按失败计入。误差线按32个场景聚类重采样，不能代表全部训练种子的波动。',
         ha='center',fontsize=10,color='#52616b')
fig.tight_layout(rect=[0,.08,1,.92])
fig.savefig(r/'challenge-results.png',dpi=160)
fig.savefig(r/'challenge-results.svg')
print('Saved matched battle result figure')
