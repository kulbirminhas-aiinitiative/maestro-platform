#!/usr/bin/env python3
"""Tests for policy_enforcer module."""

import pytest
import tempfile
import yaml
from pathlib import Path

from maestro_hive.compliance.policy_enforcer import (
    PolicyEnforcer,
    PolicyRule,
    PolicyCondition,
    PolicyEvaluation,
    Policy,
    PolicyEffect,
    get_policy_enforcer
)


class TestPolicyEnforcer:
    """Tests for PolicyEnforcer class."""

    def test_enforcer_initialization(self):
        """Test enforcer initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            enforcer = PolicyEnforcer(policy_dir=tmpdir)
            assert enforcer.policy_dir.exists()

    def test_simple_allow_policy(self):
        """Test simple allow policy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy_file = Path(tmpdir) / "allow_all.yaml"
            policy_file.write_text(yaml.dump({
                'name': 'allow-all',
                'description': 'Allow all actions',
                'rules': [
                    {
                        'id': 'rule-1',
                        'effect': 'allow',
                        'conditions': []
                    }
                ]
            }))

            enforcer = PolicyEnforcer(policy_dir=tmpdir)
            context = {
                'actor': 'user-1',
                'action': 'read',
                'resource': 'document-1'
            }

            result = enforcer.evaluate(context)
            assert result.allowed is True

    def test_deny_policy(self):
        """Test deny policy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy_file = Path(tmpdir) / "deny_admin.yaml"
            policy_file.write_text(yaml.dump({
                'name': 'deny-admin-actions',
                'description': 'Deny admin actions',
                'rules': [
                    {
                        'id': 'rule-deny',
                        'effect': 'deny',
                        'conditions': [
                            {'field': 'action', 'operator': 'equals', 'value': 'admin'}
                        ]
                    },
                    {
                        'id': 'rule-allow',
                        'effect': 'allow',
                        'conditions': []
                    }
                ]
            }))

            enforcer = PolicyEnforcer(policy_dir=tmpdir)

            # Admin action should be denied
            admin_context = {
                'actor': 'user-1',
                'action': 'admin',
                'resource': 'system'
            }
            result = enforcer.evaluate(admin_context)
            assert result.allowed is False

            # Other actions should be allowed
            read_context = {
                'actor': 'user-1',
                'action': 'read',
                'resource': 'document'
            }
            result = enforcer.evaluate(read_context)
            assert result.allowed is True

    def test_condition_operators(self):
        """Test various condition operators."""
        with tempfile.TemporaryDirectory() as tmpdir:
            enforcer = PolicyEnforcer(policy_dir=tmpdir)

            # Test equals
            cond_eq = PolicyCondition(field='action', operator='equals', value='read')
            assert enforcer._evaluate_condition(cond_eq, {'action': 'read'}) is True
            assert enforcer._evaluate_condition(cond_eq, {'action': 'write'}) is False

            # Test not_equals
            cond_neq = PolicyCondition(field='action', operator='not_equals', value='delete')
            assert enforcer._evaluate_condition(cond_neq, {'action': 'read'}) is True
            assert enforcer._evaluate_condition(cond_neq, {'action': 'delete'}) is False

            # Test contains
            cond_contains = PolicyCondition(field='roles', operator='contains', value='admin')
            assert enforcer._evaluate_condition(cond_contains, {'roles': ['admin', 'user']}) is True
            assert enforcer._evaluate_condition(cond_contains, {'roles': ['user']}) is False

            # Test in
            cond_in = PolicyCondition(field='action', operator='in', value=['read', 'write'])
            assert enforcer._evaluate_condition(cond_in, {'action': 'read'}) is True
            assert enforcer._evaluate_condition(cond_in, {'action': 'delete'}) is False

    def test_multiple_conditions_and(self):
        """Test multiple conditions with AND logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy_file = Path(tmpdir) / "multi_cond.yaml"
            policy_file.write_text(yaml.dump({
                'name': 'multi-condition',
                'rules': [
                    {
                        'id': 'rule-1',
                        'effect': 'allow',
                        'conditions': [
                            {'field': 'action', 'operator': 'equals', 'value': 'read'},
                            {'field': 'resource_type', 'operator': 'equals', 'value': 'public'}
                        ]
                    }
                ]
            }))

            enforcer = PolicyEnforcer(policy_dir=tmpdir)

            # Both conditions met
            context1 = {
                'actor': 'user',
                'action': 'read',
                'resource': 'doc',
                'resource_type': 'public'
            }
            assert enforcer.evaluate(context1).allowed is True

            # Only one condition met
            context2 = {
                'actor': 'user',
                'action': 'read',
                'resource': 'doc',
                'resource_type': 'private'
            }
            assert enforcer.evaluate(context2).allowed is False

    def test_no_matching_rule_default_deny(self):
        """Test default deny when no rules match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy_file = Path(tmpdir) / "strict.yaml"
            policy_file.write_text(yaml.dump({
                'name': 'strict-policy',
                'rules': [
                    {
                        'id': 'rule-1',
                        'effect': 'allow',
                        'conditions': [
                            {'field': 'action', 'operator': 'equals', 'value': 'read'}
                        ]
                    }
                ]
            }))

            enforcer = PolicyEnforcer(policy_dir=tmpdir)

            # Non-matching action should be denied (default)
            context = {'actor': 'user', 'action': 'delete', 'resource': 'doc'}
            result = enforcer.evaluate(context)
            assert result.allowed is False

    def test_add_policy_programmatically(self):
        """Test adding policy programmatically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            enforcer = PolicyEnforcer(policy_dir=tmpdir)

            rule = PolicyRule(
                id='dynamic-rule',
                effect=PolicyEffect.ALLOW,
                conditions=[
                    PolicyCondition(field='actor', operator='equals', value='admin')
                ]
            )

            enforcer.add_rule(rule)

            admin_context = {'actor': 'admin', 'action': 'any', 'resource': 'any'}
            assert enforcer.evaluate(admin_context).allowed is True

            user_context = {'actor': 'user', 'action': 'any', 'resource': 'any'}
            assert enforcer.evaluate(user_context).allowed is False

    def test_get_policy_enforcer_factory(self):
        """Test factory function."""
        enforcer = get_policy_enforcer()
        assert isinstance(enforcer, PolicyEnforcer)


class TestPolicyCondition:
    """Tests for PolicyCondition dataclass."""

    def test_condition_creation(self):
        """Test condition creation."""
        condition = PolicyCondition(
            field='actor',
            operator='equals',
            value='admin'
        )
        assert condition.field == 'actor'
        assert condition.operator == 'equals'
        assert condition.value == 'admin'

    def test_condition_to_dict(self):
        """Test condition serialization."""
        condition = PolicyCondition(
            field='action',
            operator='in',
            value=['read', 'write']
        )
        data = condition.to_dict()
        assert data['field'] == 'action'
        assert data['operator'] == 'in'


class TestPolicyEvaluation:
    """Tests for PolicyEvaluation dataclass."""

    def test_evaluation_allowed(self):
        """Test allowed evaluation."""
        evaluation = PolicyEvaluation(
            allowed=True,
            matched_rule='rule-1',
            reason='Matched allow rule'
        )
        assert evaluation.allowed is True
        assert evaluation.matched_rule == 'rule-1'

    def test_evaluation_denied(self):
        """Test denied evaluation."""
        evaluation = PolicyEvaluation(
            allowed=False,
            matched_rule='rule-deny',
            reason='Explicit deny'
        )
        assert evaluation.allowed is False

    def test_evaluation_to_dict(self):
        """Test evaluation serialization."""
        evaluation = PolicyEvaluation(
            allowed=True,
            matched_rule='rule-1',
            reason='Access granted'
        )
        data = evaluation.to_dict()
        assert data['allowed'] is True
        assert data['matched_rule'] == 'rule-1'
