from __future__ import annotations

import textwrap

from nanobot.agent.facts_index import build_index


def test_build_index_basic():
    md = textwrap.dedent(
        """
        # Profile
        Name: Maolaohei
        喜好: 草莓味甜甜圈
        token: should be filtered
        
        ## Project
        repo: github.com/Maolaohei
        其它：不规则行
        """
    )
    facts = build_index(md)
    ks = [f.k for f in facts]
    vs = [f.v for f in facts]
    assert "Name" in ks
    assert "喜好" in ks or "偏好" in "".join(ks)
    assert "repo" in ks
    assert all("should be filtered" not in v for v in vs)


def test_build_index_ignore_codeblock():
    md = textwrap.dedent(
        """
        正常: 行
        ```
        password: 123
        another: 456
        ```
        有效: 是
        """
    )
    facts = build_index(md)
    ks = [f.k for f in facts]
    assert "正常" in ks and "有效" in ks and "password" not in ks
