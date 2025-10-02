import requests
from bs4 import BeautifulSoup
import hashlib
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PageChangeDetector:
    def __init__(self, settings):
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def check_certification(self, cert_id, cert_config, previous_snapshot):
        """Check a single certification page for changes"""
        try:
            logger.info(f"Checking {cert_config['name']} ({cert_config['code']})...")
            
            response = self.session.get(cert_config['url'], timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            current_snapshot = self.extract_cert_info(soup, cert_config)
            current_snapshot['url'] = cert_config['url']
            current_snapshot['checked_at'] = datetime.now().isoformat()
            
            if previous_snapshot:
                changes = self.detect_changes(previous_snapshot, current_snapshot, cert_config)
                
                if changes:
                    logger.info(f"  ✓ {len(changes)} change(s) detected")
                    return {
                        'cert_id': cert_id,
                        'name': cert_config['name'],
                        'code': cert_config['code'],
                        'provider': cert_config.get('provider', 'Unknown'),
                        'url': cert_config['url'],
                        'changes': changes,
                        'snapshot': current_snapshot
                    }
                else:
                    logger.info(f"  ✓ No changes")
            else:
                logger.info(f"  ✓ First check - baseline created")
                # Don't send notification on first check
                return {
                    'cert_id': cert_id,
                    'snapshot': current_snapshot,
                    'is_baseline': True
                }
            
            return {
                'cert_id': cert_id,
                'snapshot': current_snapshot
            }
        
        except Exception as e:
            logger.error(f"  ✗ Error: {str(e)}")
            return None
    
    def extract_cert_info(self, soup, cert_config):
        """Extract key information from certification page"""
        text = soup.get_text()
        
        info = {
            'content_hash': hashlib.md5(text.encode()).hexdigest(),
            'title': soup.find('title').get_text() if soup.find('title') else '',
        }
        
        # Extract exam codes (e.g., C03, AZ-104, SY0-701)
        exam_patterns = [
            r'\b(C0[2-9])\b',  # AWS: C02, C03, C04
            r'\b([A-Z]{2,4}-\d{3,4})\b',  # Azure/others: AZ-104, SY0-701
            r'\b(TA-\d{3}|VA-\d{3}|CA-\d{3})\b',  # HashiCorp
        ]
        
        codes = set()
        for pattern in exam_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            codes.update(matches)
        
        if codes:
            info['exam_codes'] = sorted(list(codes))[:10]
        
        # Extract retirement/expiry dates
        date_patterns = [
            r'retir(?:ing|ed|ement).*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'available until.*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'expir(?:es|ing).*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'ends? on.*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        
        dates = set()
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.update(matches)
        
        if dates:
            info['important_dates'] = sorted(list(dates))[:5]
        
        # Extract Kubernetes version
        k8s_match = re.search(r'Kubernetes\s+(?:version\s+)?(\d+\.\d+)', text, re.IGNORECASE)
        if k8s_match:
            info['kubernetes_version'] = k8s_match.group(1)
        
        # Extract main headings
        headings = soup.find_all(['h1', 'h2', 'h3'])
        info['headings'] = [h.get_text().strip()[:100] for h in headings[:15]]
        
        return info
    
    def detect_changes(self, old, new, cert_config):
        """Detect specific changes between snapshots"""
        changes = []
        
        # 1. Check exam code changes
        old_codes = set(old.get('exam_codes', []))
        new_codes = set(new.get('exam_codes', []))
        
        added_codes = new_codes - old_codes
        removed_codes = old_codes - new_codes
        
        if added_codes:
            changes.append(f"New exam version: {', '.join(added_codes)}")
        
        if removed_codes:
            changes.append(f"Exam version removed: {', '.join(removed_codes)}")
        
        # 2. Check important dates
        old_dates = set(old.get('important_dates', []))
        new_dates = set(new.get('important_dates', []))
        
        added_dates = new_dates - old_dates
        
        if added_dates:
            changes.append(f"Important date(s) announced: {', '.join(added_dates)}")
        
        # 3. Check Kubernetes version
        old_k8s = old.get('kubernetes_version')
        new_k8s = new.get('kubernetes_version')
        
        if old_k8s and new_k8s and old_k8s != new_k8s:
            changes.append(f"Kubernetes version updated: {old_k8s} → {new_k8s}")
        
        # 4. Check title changes
        if old.get('title') != new.get('title'):
            changes.append("Certification page title updated")
        
        # 5. Check for significant content changes
        if old.get('content_hash') != new.get('content_hash'):
            # Only report if no specific changes found above
            if not changes:
                # Check if headings changed significantly
                old_headings = set(old.get('headings', []))
                new_headings = set(new.get('headings', []))
                
                if len(new_headings - old_headings) >= 2:
                    changes.append("Significant page content updated")
        
        return changes
