"""Visible legal WAIT ordering; public counter events are a declared input.

Uses no native remaining-counter count, hidden state or future randomness.
An ambiguous cross-round batch cannot certify a spent counter this round.
"""
from vcmi_gym.envs.v15.vcmi_env import Unit, Action, ACTION_TYPES
from experts_events import assess


class WaitBait:
    def __init__(self, mode='wait-bait'):
        self.mode=mode
        self.initial_max=None
        self.round=None
        self.counter_spent=set()
        self.node_ids={}

    def observe(self,batch,mapping):
        self.node_ids=dict(mapping)
        current=batch['round_after']
        if current!=self.round:
            self.round=current
            self.counter_spent.clear()
        if batch['round_before']==batch['round_after']:
            self.counter_spent.update(e['attacker_id'] for e in batch['events']
                                      if e['kind']==2 and e.get('attack_flags',0)&2)

    def choose(self,obs):
        units=Unit.decode_many(obs['nodes']['Unit'])
        legal=[int(a) for a in obs['active_action_ids']]
        baseline=int(obs['teacher_action_id'])
        assert baseline in legal
        facts=assess(obs)
        own=[u.VALUE_REL for u in units if not u.IS_ENEMY]
        if self.initial_max is None:
            self.initial_max=max(own)
        actor=facts[baseline]['actor_node']
        value=units[actor].VALUE_REL
        kind=lambda a:int(Action.decode_one(obs['nodes']['Action'][a]).ACTION_TYPE)
        waits=[a for a in legal if kind(a)==ACTION_TYPES['WAIT']]
        melee=[a for a in legal if kind(a)==ACTION_TYPES['AMOVE'] and facts[a]['primary']]
        primary=lambda a:facts[a]['primary'][0]
        target_value=lambda a:units[primary(a)].VALUE_REL
        action=baseline
        reason='teacher_fallback'
        if self.mode=='counter-bait':
            # Focus the threatening main stack when it is legally attackable,
            # rather than voluntarily moving/attacking into a low-value lure.
            if melee and kind(baseline)==ACTION_TYPES['AMOVE']:
                best=max(melee,key=target_value)
                if target_value(best)>4*target_value(baseline):
                    action=best;reason='attack_visible_main_instead_of_low_value_lure'
        elif value<=.15*self.initial_max:
            if melee:
                best=max(melee,key=target_value)
                if target_value(best)>0:
                    action=best;reason='low_value_first_melee'
        elif waits and melee and kind(baseline)==ACTION_TYPES['AMOVE']:
            # All graph Action nodes include other units' hypothetical current
            # legal movement/attack choices; only active_action_ids are issued.
            # Require a specific low-value unit's existing AMOVE to THE SAME
            # target and queue evidence that it still acts this round.
            by={int(a):int(u) for a,u in obs['edges'][('Action','By','Unit')]['index'].T}
            before={int(dst) for (src,dst),attr in zip(
                obs['edges'][('Unit','ActsBefore','Unit')]['index'].T,
                obs['edges'][('Unit','ActsBefore','Unit')]['attrs'])
                if int(src)==actor and float(attr[0])*2<=1.001}
            target_node=primary(baseline)
            reachable_low=[]
            relation=obs['edges'][('Unit','IsMeleedBy','Action')]
            for (victim,hypo),attr in zip(relation['index'].T,relation['attrs']):
                hypo=int(hypo);low=by[hypo]
                # IS_PRIMARY_TARGET is the first two-column categorical attr.
                is_primary=bool(attr[1]>attr[0])
                if int(victim)==target_node and is_primary and low in before and not units[low].IS_ENEMY \
                   and units[low].VALUE_REL<=.15*self.initial_max and kind(hypo)==ACTION_TYPES['AMOVE']:
                    reachable_low.append(low)
            low_alive=bool(reachable_low)
            target=self.node_ids.get(primary(baseline))
            target_still_acts_this_round=target_node in before
            if low_alive and target not in self.counter_spent and not target_still_acts_this_round:
                action=waits[0];reason='wait_main_for_low_value_counter_consumption'
        return action,dict(version='wait-bait-v3-tempo-safe' if self.mode!='counter-bait' else 'counter-bait-v3',
                           certified=False,reason=reason,overrode_teacher=action!=baseline,
                           teacher_action=baseline,public_observed_spent_ids=sorted(self.counter_spent))
