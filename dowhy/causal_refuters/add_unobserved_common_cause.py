import copy

import numpy as np
import pandas as pd

from dowhy.causal_refuter import CausalRefutation
from dowhy.causal_refuter import CausalRefuter


class AddUnobservedCommonCause(CausalRefuter):

    """Add an unobserved confounder for refutation.

    TODO: Needs scaled version of the parameters and an interpretation module
    (e.g., in comparison to biggest effect of known confounder)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.effect_on_t = kwargs["confounders_effect_on_treatment"] if "confounders_effect_on_treatment" in kwargs else "binary_flip"
        self.effect_on_y = kwargs["confounders_effect_on_outcome"] if "confounders_effect_on_outcome" in kwargs else "linear"
        self.kappa_t = kwargs["effect_strength_on_treatment"]
        self.kappa_y = kwargs["effect_strength_on_outcome"]

    def refute_estimate(self):
        new_data = copy.deepcopy(self._data)
        new_data = self.include_confounders_effect(new_data)

        estimator_class = self._estimate.params['estimator_class']
        new_estimator = estimator_class(
            new_data,
            self._target_estimand,
            self._treatment_name, self._outcome_name,
            test_significance=None
        )
        new_effect = new_estimator.estimate_effect()
        refute = CausalRefutation(self._estimate.value, new_effect.value,
                                  refutation_type="Refute: Add an Unobserved Common Cause")
        return refute

    def include_confounders_effect(self, new_data):
        num_rows = self._data.shape[0]
        w_random=np.random.randn(num_rows)

        if self.effect_on_t == "binary_flip":
            new_data['temp_rand_no'] = np.random.random(num_rows)
            new_data.loc[new_data['temp_rand_no'] <= self.kappa_t, self._treatment_name ]  = 1- new_data[self._treatment_name]
            new_data.pop('temp_rand_no')
        elif self.effect_on_t == "linear":
            confounder_t_effect = self.kappa_t * w_random
            new_data[self._treatment_name] = new_data[self._treatment_name].values - np.ndarray(shape=(num_rows,1), buffer=confounder_t_effect)
        else:
            raise NotImplementedError("'" + self.effect_on_t + "' method not supported for confounders' effect on treatment")

        if self.effect_on_y == "binary_flip":
            new_data['temp_rand_no'] = np.random.random(num_rows)
            new_data.loc[new_data['temp_rand_no'] <= self.kappa_y, self._outcome_name ]  = 1- new_data[self._outcome_name]
            new_data.pop('temp_rand_no')
        elif self.effect_on_y == "linear":
            confounder_y_effect = self.kappa_y * w_random
            new_data[self._outcome_name] = new_data[self._outcome_name].values - np.ndarray(shape=(num_rows,1), buffer=confounder_y_effect)
        else:
            raise NotImplementedError("'" + self.effect_on_y+ "' method not supported for confounders' effect on outcome")
        return new_data

if __name__=="__main__":
    import dowhy.datasets
    from dowhy.do_why import CausalModel
    data =  dowhy.datasets.linear_dataset(beta=10,num_common_causes=5,
            num_instruments = 2,
            num_samples=1000,
            treatment_is_binary=True)
    df = data["df"]
    # Without graph
    model= CausalModel( data=df,
            treatment=data["treatment_name"],
            outcome=data["outcome_name"],
            common_causes=data["common_causes_names"])
    identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(identified_estimand,
            method_name="backdoor.propensity_score_matching")
    print(estimate)
    print("Causal Estimate is " + str(estimate.value))
    res_unobserved=model.refute_estimate(identified_estimand, estimate,
            method_name="add_unobserved_common_cause",
            effect_strength_on_treatment =0.5,
            effect_strength_on_outcome=0.5)
    print(res_unobserved)
