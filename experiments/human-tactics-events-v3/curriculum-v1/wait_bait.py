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
            low_alive=any(not u.IS_ENEMY and u.VALUE_REL<=.15*self.initial_max for u in units)
            target=self.node_ids.get(primary(baseline))
            if low_alive and target not in self.counter_spent:
                action=waits[0];reason='wait_main_for_low_value_counter_consumption'
        return action,dict(version='wait-bait-v1' if self.mode!='counter-bait' else 'counter-bait-v1',
                           certified=False,reason=reason,overrode_teacher=action!=baseline,
                           teacher_action=baseline,public_observed_spent_ids=sorted(self.counter_spent))
