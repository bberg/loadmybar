#!/bin/bash
# Domain availability checker - DNS + WHOIS
# Usage: ./domain_check.sh domain1.com domain2.com domain3.com

echo "Domain Availability Check"
echo "========================="
echo ""

for domain in "$@"; do
    # DNS check first (fast)
    if host "$domain" > /dev/null 2>&1; then
        echo "❌ $domain - DNS resolves (likely taken)"
    else
        # No DNS - verify with WHOIS for .com domains
        if [[ "$domain" == *.com ]]; then
            result=$(whois "$domain" 2>/dev/null)
            if echo "$result" | grep -qi "No match\|NOT FOUND\|No Data Found\|Domain not found"; then
                echo "✅ $domain - AVAILABLE (WHOIS confirmed)"
            elif echo "$result" | grep -qi "Domain Status:"; then
                echo "⚠️  $domain - Registered but no DNS (parked?)"
            else
                echo "?  $domain - No DNS, WHOIS unclear - check manually"
            fi
        else
            echo "?  $domain - No DNS (check registrar for non-.com)"
        fi
    fi
done
