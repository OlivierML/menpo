from scipy.linalg import norm
import numpy as np
from pybug.lucaskanade.appearance.base import AppearanceLucasKanade


class ProbabilisticForwardAdditive(AppearanceLucasKanade):

    type = 'ProbFA'

    def _align(self, lk_fitting, max_iters=20, project=True):
        # Initial error > eps
        error = self.eps + 1
        image = lk_fitting.image
        n_iters = 0

        # Forward Additive Algorithm
        while n_iters < max_iters and error > self.eps:
            # Compute warped image with current parameters
            IWxp = image.warp_to(self.template.mask, self.transform,
                                 interpolator=self._interpolator)

            # Compute warp Jacobian
            dW_dp = self.transform.jacobian(
                self.template.mask.true_indices)

            # Compute steepest descent images, VI_dW_dp
            J = self.residual.steepest_descent_images(
                image, dW_dp, forward=(self.template, self.transform,
                                       self._interpolator))

            # Project out appearance model from VT_dW_dp
            self._J = (self.appearance_model.distance_to_subspace_vector(J.T) +
                       self.appearance_model.project_whitened_vector(J.T)).T

            # Compute Hessian and inverse
            self._H = self.residual.calculate_hessian(self._J, J2=J)

            # Compute steepest descent parameter updates
            sd_delta_p = self.residual.steepest_descent_update(
                self._J, self.template, IWxp)

            # Compute gradient descent parameter updates
            delta_p = np.real(self._calculate_delta_p(sd_delta_p))

            # Update warp parameters
            parameters = self.transform.as_vector() + delta_p
            self.transform.from_vector_inplace(parameters)
            lk_fitting.parameters.append(parameters)

            # Test convergence
            error = np.abs(norm(delta_p))
            n_iters += 1

        lk_fitting.fitted = True
        return self.transform


class ProbabilisticForwardCompositional(AppearanceLucasKanade):

    type = 'ProbFC'

    def _precompute(self):
        # Compute warp Jacobian
        self._dW_dp = self.transform.jacobian(
            self.template.mask.true_indices)

    def _align(self, lk_fitting, max_iters=20, project=True):
        # Initial error > eps
        error = self.eps + 1
        image = lk_fitting.image
        n_iters = 0

        # Forward Additive Algorithm
        while n_iters < max_iters and error > self.eps:
            # Compute warped image with current parameters
            IWxp = image.warp_to(self.template.mask, self.transform,
                                 interpolator=self._interpolator)

            # Compute steepest descent images, VI_dW_dp
            J = self.residual.steepest_descent_images(IWxp, self._dW_dp)

            # Project out appearance model from VT_dW_dp
            self._J = (self.appearance_model.distance_to_subspace_vector(J.T) +
                       self.appearance_model.project_whitened_vector(J.T)).T

            # Compute Hessian and inverse
            self._H = self.residual.calculate_hessian(self._J, J2=J)

            # Compute steepest descent parameter updates
            sd_delta_p = self.residual.steepest_descent_update(
                self._J, self.template, IWxp)

            # Compute gradient descent parameter updates
            delta_p = np.real(self._calculate_delta_p(sd_delta_p))

            # Update warp parameters
            self.transform.compose_after_from_vector_inplace(delta_p)
            lk_fitting.parameters.append(self.transform.as_vector())

            # Test convergence
            error = np.abs(norm(delta_p))
            n_iters += 1

        lk_fitting.fitted = True
        return self.transform


class ProbabilisticInverseCompositional(AppearanceLucasKanade):

    type = 'ProbIC'

    def _precompute(self):
        # Compute warp Jacobian
        self._dW_dp = self.transform.jacobian(
            self.template.mask.true_indices)

        # Compute steepest descent images, VT_dW_dp
        J = self.residual.steepest_descent_images(self.template,
                                                  self._dW_dp)
        # Project out appearance model from VT_dW_dp
        self._J = (self.appearance_model.distance_to_subspace_vector(J.T) +
                   self.appearance_model.project_whitened_vector(J.T)).T
        # Compute Hessian and inverse
        self._H = self.residual.calculate_hessian(self._J, J2=J)

    def _align(self, lk_fitting, max_iters=20, project=True):
        # Initial error > eps
        error = self.eps + 1
        image = lk_fitting.image
        n_iters = 0

        # Baker-Matthews, Inverse Compositional Algorithm
        while n_iters < max_iters and error > self.eps:
            # Compute warped image with current parameters
            IWxp = image.warp_to(self.template.mask, self.transform,
                                 interpolator=self._interpolator)

            # Compute steepest descent parameter updates
            sd_delta_p = self.residual.steepest_descent_update(
                self._J, IWxp, self.template)

            # Compute gradient descent parameter updates
            delta_p = np.real(self._calculate_delta_p(sd_delta_p))

            # Request the pesudoinverse vector from the transform
            inv_delta_p = self.transform.pseudoinverse_vector(delta_p)

            # Update warp parameters
            self.transform.compose_after_from_vector_inplace(inv_delta_p)
            lk_fitting.parameters.append(self.transform.as_vector())

            # Test convergence
            error = np.abs(norm(delta_p))
            n_iters += 1

        lk_fitting.fitted = True
        return self.transform
