# Copyright (C) 2009-2010 Power System Engineering Research Center
# Copyright (C) 2010 Richard Lincoln
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from numpy import Inf, ones, zeros, dot

from scipy.sparse import csr_matrix

from pips import pips

def qps_pips(H, c, A, l, u, xmin=None, xmax=None, x0=None, opt=None):
    """Uses the Python Interior Point Solver (PIPS) to solve the following
    QP (quadratic programming) problem::

            min 1/2 x'*H*x + C'*x
             x

    subject to::

            l <= A*x <= u       (linear constraints)
            xmin <= x <= xmax   (variable bounds)

    Note the calling syntax is almost identical to that of QUADPROG from
    MathWorks' Optimization Toolbox. The main difference is that the linear
    constraints are specified with C{A}, C{L}, C{U} instead of C{A}, C{B},
    C{Aeq}, C{Beq}.

    See also L{pips}.

    Example from U{http://www.uc.edu/sashtml/iml/chap8/sect12.htm}:

        >>> from numpy import array, zeros, Inf
        >>> from scipy.sparse import csr_matrix
        >>> H = csr_matrix(array([[1003.1,  4.3,     6.3,     5.9],
        ...                       [4.3,     2.2,     2.1,     3.9],
        ...                       [6.3,     2.1,     3.5,     4.8],
        ...                       [5.9,     3.9,     4.8,     10 ]]))
        >>> c = zeros(4)
        >>> A = csr_matrix(array([[1,       1,       1,       1   ],
        ...                       [0.17,    0.11,    0.10,    0.18]]))
        >>> l = array([1, 0.10])
        >>> u = array([1, Inf])
        >>> xmin = zeros(4)
        >>> xmax = None
        >>> x0 = array([1, 0, 0, 1])
        >>> solution = qps_pips(H, c, A, l, u, xmin, xmax, x0)
        >>> round(solution["f"], 11) == 1.09666678128
        True
        >>> solution["converged"]
        True
        >>> solution["output"]["iterations"]
        10

    All parameters are optional except C{H}, C{C}, C{A} and C{L}.
    @param H: Quadratic cost coefficients.
    @type H: csr_matrix
    @param c: vector of linear cost coefficients
    @type c: array
    @param A: Optional linear constraints.
    @type A: csr_matrix
    @param l: Optional linear constraints. Default values are M{-Inf}.
    @type l: array
    @param u: Optional linear constraints. Default values are M{Inf}.
    @type u: array
    @param xmin: Optional lower bounds on the M{x} variables, defaults are
                 M{-Inf}.
    @type xmin: array
    @param xmax: Optional upper bounds on the M{x} variables, defaults are
                 M{Inf}.
    @type xmax: array
    @param x0: Starting value of optimization vector M{x}.
    @type x0: array
    @param opt: optional options dictionary with the following keys, all of
                which are also optional (default values shown in parentheses)
                  - C{verbose} (False) - Controls level of progress output
                    displayed
                  - C{feastol} (1e-6) - termination tolerance for feasibility
                    condition
                  - C{gradtol} (1e-6) - termination tolerance for gradient
                    condition
                  - C{comptol} (1e-6) - termination tolerance for
                    complementarity condition
                  - C{costtol} (1e-6) - termination tolerance for cost
                    condition
                  - C{max_it} (150) - maximum number of iterations
                  - C{step_control} (False) - set to True to enable step-size
                    control
                  - C{max_red} (20) - maximum number of step-size reductions if
                    step-control is on
                  - C{cost_mult} (1.0) - cost multiplier used to scale the
                    objective function for improved conditioning. Note: The
                    same value must also be passed to the Hessian evaluation
                    function so that it can appropriately scale the objective
                    function term in the Hessian of the Lagrangian.
    @type opt: dict

    @rtype: dict
    @return: The solution dictionary has the following keys:
               - C{x} - solution vector
               - C{f} - final objective function value
               - C{converged} - exit status
                   - True = first order optimality conditions satisfied
                   - False = maximum number of iterations reached
                   - None = numerically failed
               - C{output} - output dictionary with keys:
                   - C{iterations} - number of iterations performed
                   - C{hist} - dictionary of arrays with trajectories of the
                     following: feascond, gradcond, compcond, costcond, gamma,
                     stepsize, obj, alphap, alphad
                   - C{message} - exit message
               - C{lmbda} - dictionary containing the Langrange and Kuhn-Tucker
                 multipliers on the constraints, with keys:
                   - C{eqnonlin} - non-linear equality constraints
                   - C{ineqnonlin} - non-linear inequality constraints
                   - C{mu_l} - lower (left-hand) limit on linear constraints
                   - C{mu_u} - upper (right-hand) limit on linear constraints
                   - C{lower} - lower bound on optimization variables
                   - C{upper} - upper bound on optimization variables

    @license: Apache License version 2.0
    """
    if H is None or H.nnz == 0:
        if A is None or A.nnz == 0 and \
           xmin is None or len(xmin) == 0 and \
           xmax is None or len(xmax) == 0:
            print 'qps_pips: LP problem must include constraints or variable bounds'
            return
        else:
            if A is not None and A.nnz >= 0:
                nx = A.shape[1]
            elif xmin is not None and len(xmin) > 0:
                nx = xmin.shape[0]
            elif xmax is not None and len(xmax) > 0:
                nx = xmax.shape[0]
        H = csr_matrix((nx, nx))
    else:
        nx = H.shape[0]

    xmin = -Inf * ones(nx) if xmin is None else xmin
    xmax =  Inf * ones(nx) if xmax is None else xmax

    c = zeros(nx) if c is None else c

#    if x0 is None:
#        x0 = zeros(nx)
#        k = flatnonzero( (VUB < 1e10) & (VLB > -1e10) )
#        x0[k] = ((VUB[k] + VLB[k]) / 2)
#        k = flatnonzero( (VUB < 1e10) & (VLB <= -1e10) )
#        x0[k] = VUB[k] - 1
#        k = flatnonzero( (VUB >= 1e10) & (VLB > -1e10) )
#        x0[k] = VLB[k] + 1

    x0 = zeros(nx) if x0 is None else x0

    opt = {} if opt is None else opt
    if not opt.has_key("cost_mult"):
        opt["cost_mult"] = 1

    def qp_f(x):
        f = 0.5 * dot(x.T * H, x) + dot(c.T, x)
        df = H * x + c
        d2f = H
        return f, df, d2f

#    def qp_gh(x):
#        g = array([])
#        h = array([])
#        dg = None
#        dh = None
#        return g, h, dg, dh
#
#    def qp_hessian(x, lmbda):
#        Lxx = H * opt["cost_mult"]
#        return Lxx

#    l = -Inf * ones(b.shape[0])
#    l[:N] = b[:N]

    return pips(qp_f, x0, A, l, u, xmin, xmax, opt=opt)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
