from unittest import TestCase
from hvac import exceptions

from tests.utils.hvac_integration_test_case import HvacIntegrationTestCase


class TestToken(HvacIntegrationTestCase, TestCase):
    def test_auth_token_manipulation(self):
        result = self.client.auth.token.create(ttl="1h", renewable=True)
        assert result["auth"]["client_token"]

        lookup = self.client.auth.token.lookup(result["auth"]["client_token"])
        assert result["auth"]["client_token"] == lookup["data"]["id"]

        renew = self.client.auth.token.renew(lookup["data"]["id"])
        assert result["auth"]["client_token"] == renew["auth"]["client_token"]

        self.client.auth.token.revoke(lookup["data"]["id"])

        try:
            lookup = self.client.auth.token.lookup(result["auth"]["client_token"])
            assert False
        except exceptions.Forbidden:
            assert True
        except exceptions.InvalidPath:
            assert True
        except exceptions.InvalidRequest:
            assert True

    def test_self_auth_token_manipulation(self):
        result = self.client.auth.token.create(ttl="1h", renewable=True)
        assert result["auth"]["client_token"]
        self.client.token = result["auth"]["client_token"]

        lookup = self.client.auth.token.lookup_self()
        assert result["auth"]["client_token"] == lookup["data"]["id"]

        renew = self.client.auth.token.renew_self()
        assert result["auth"]["client_token"] == renew["auth"]["client_token"]

        self.client.auth.token.revoke_self()

        try:
            lookup = self.client.auth.token.lookup(result["auth"]["client_token"])
            assert False
        except exceptions.Forbidden:
            assert True
        except exceptions.InvalidPath:
            assert True
        except exceptions.InvalidRequest:
            assert True

    def test_auth_orphaned_token_manipulation(self):
        result = self.client.auth.token.create_orphan(ttl="1h", renewable=True)
        assert result["auth"]["client_token"]

        lookup = self.client.auth.token.lookup(result["auth"]["client_token"])
        assert result["auth"]["client_token"] == lookup["data"]["id"]

        renew = self.client.auth.token.renew(lookup["data"]["id"])
        assert result["auth"]["client_token"] == renew["auth"]["client_token"]

        self.client.auth.token.revoke(lookup["data"]["id"])

        try:
            lookup = self.client.auth.token.lookup(result["auth"]["client_token"])
            assert False
        except exceptions.Forbidden:
            assert True
        except exceptions.InvalidPath:
            assert True
        except exceptions.InvalidRequest:
            assert True

    def test_token_accessor(self):
        # Create token, check accessor is provided
        result = self.client.auth.token.create(ttl="1h")
        token_accessor = result["auth"].get("accessor", None)
        assert token_accessor

        # Look up token by accessor, make sure token is excluded from results
        lookup = self.client.auth.token.lookup_accessor(token_accessor)
        assert lookup["data"]["accessor"] == token_accessor
        assert not lookup["data"]["id"]

        # Revoke token using the accessor
        self.client.auth.token.revoke_accessor(token_accessor)

        # Look up by accessor should fail
        with self.assertRaises(exceptions.InvalidRequest):
            lookup = self.client.auth.token.lookup_accessor(token_accessor)

        # As should regular lookup
        with self.assertRaises(exceptions.Forbidden):
            lookup = self.client.auth.token.lookup(result["auth"]["client_token"])

    def test_create_token_explicit_max_ttl(self):

        token = self.client.auth.token.create(ttl="30m", explicit_max_ttl="5m")

        assert token["auth"]["client_token"]

        assert token["auth"]["lease_duration"] == 300

        # Validate token
        lookup = self.client.auth.token.lookup(token["auth"]["client_token"])
        assert token["auth"]["client_token"] == lookup["data"]["id"]

    def test_create_token_max_ttl(self):

        token = self.client.auth.token.create(ttl="5m")

        assert token["auth"]["client_token"]

        assert token["auth"]["lease_duration"] == 300

        # Validate token
        lookup = self.client.auth.token.lookup(token["auth"]["client_token"])
        assert token["auth"]["client_token"] == lookup["data"]["id"]

    def test_create_token_periodic(self):

        token = self.client.auth.token.create(period="30m")

        assert token["auth"]["client_token"]

        assert token["auth"]["lease_duration"] == 1800

        # Validate token
        lookup = self.client.auth.token.lookup(token["auth"]["client_token"])
        assert token["auth"]["client_token"] == lookup["data"]["id"]
        assert lookup["data"]["period"] == 1800

    def test_token_roles(self):
        # No roles, list_token_roles == None
        with self.assertRaises(exceptions.InvalidPath):
            self.client.auth.token.list_roles()

        # Create token role
        assert (
            self.client.auth.token.create_or_update_role("testrole").status_code == 204
        )

        # List token roles
        during = self.client.auth.token.list_roles()["data"]["keys"]
        assert len(during) == 1
        assert during[0] == "testrole"

        # Delete token role
        self.client.auth.token.delete_role("testrole")

        # No roles, list_token_roles == None
        with self.assertRaises(exceptions.InvalidPath):
            self.client.auth.token.list_roles()

    def test_create_token_w_role(self):
        # Create policy
        self.prep_policy("testpolicy")

        # Create token role w/ policy
        assert (
            self.client.auth.token.create_or_update_role(
                "testrole", allowed_policies="testpolicy"
            ).status_code
            == 204
        )

        # Create token against role
        token = self.client.auth.token.create(ttl="1h", role_name="testrole")
        assert token["auth"]["client_token"]
        assert token["auth"]["policies"] == ["default", "testpolicy"]

        # Cleanup
        self.client.auth.token.delete_role("testrole")
        self.client.sys.delete_policy("testpolicy")
