"""Print a Firebase custom token for one existing user (the video's onboarding scene, tools/video).

The token signs that user in for an hour; it is printed for a recorder to read from the environment
and is never written to a file. Signing needs `iam.serviceAccounts.signBlob` on the service account
named by --signer (the web service's account by default).

Usage: uv run python -m scripts.custom_token --email owner@example.com
"""

import argparse
import sys

from app.core.settings import Settings

DEFAULT_SIGNER = "kredibel-web@{project}.iam.gserviceaccount.com"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--signer", default=None, help="Service account that signs the token")
    args = parser.parse_args(argv)

    import firebase_admin
    from firebase_admin import auth

    project = Settings().google_cloud_project
    signer = args.signer or DEFAULT_SIGNER.format(project=project)
    firebase_admin.initialize_app(options={"projectId": project, "serviceAccountId": signer})
    user = auth.get_user_by_email(args.email)
    sys.stdout.write(auth.create_custom_token(user.uid).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
