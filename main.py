import logging
import yaml
import json
import os
from datetime import datetime
from monitors.page_change_detector import PageChangeDetector
from utils.notifier import Notifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CertificationMonitor:
    def __init__(self):
        self.load_config()
        self.detector = PageChangeDetector(self.settings)
        self.notifier = Notifier(self.settings['notification'])
        self.snapshot_file = self.settings.get('storage', {}).get('path', 'data/cert_snapshots.json')
    
    def load_config(self):
        with open('config/certifications.yaml', 'r') as f:
            config = yaml.safe_load(f)
            self.certifications = config['certifications']
        
        with open('config/settings.yaml', 'r') as f:
            self.settings = yaml.safe_load(f)
    
    def load_snapshots(self):
        """Load previous snapshots"""
        if os.path.exists(self.snapshot_file):
            try:
                with open(self.snapshot_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load snapshots: {e}")
        return {}
    
    def save_snapshots(self, snapshots):
        """Save snapshots"""
        os.makedirs(os.path.dirname(self.snapshot_file), exist_ok=True)
        with open(self.snapshot_file, 'w') as f:
            json.dump(snapshots, f, indent=2)
    
    def scan_all_certifications(self):
        """Scan all certifications for changes"""
        logger.info("=" * 70)
        logger.info("🔍 KodeKloud Certification Monitor")
        logger.info(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info(f"📋 Monitoring {len(self.certifications)} certifications")
        logger.info("=" * 70)
        
        previous_snapshots = self.load_snapshots()
        new_snapshots = {}
        changes_detected = []
        
        for cert_id, cert_config in self.certifications.items():
            previous = previous_snapshots.get(cert_id)
            result = self.detector.check_certification(cert_id, cert_config, previous)
            
            if result:
                new_snapshots[cert_id] = result.get('snapshot')
                
                # Only add to changes if not baseline and has actual changes
                if result.get('changes') and not result.get('is_baseline'):
                    changes_detected.append(result)
        
        # Save snapshots
        self.save_snapshots(new_snapshots)
        
        # Send notifications
        logger.info("\n" + "=" * 70)
        if changes_detected:
            logger.info(f"✅ Found {len(changes_detected)} certification(s) with changes")
            
            # Group by provider for summary
            by_provider = {}
            for change in changes_detected:
                provider = change.get('provider', 'Other')
                by_provider.setdefault(provider, []).append(change)
            
            for provider, items in by_provider.items():
                logger.info(f"   {provider}: {len(items)} update(s)")
            
            self.notifier.send_notification(changes_detected)
            logger.info("📧 Notification sent")
        else:
            logger.info("✅ No changes detected - all certifications stable")
        
        logger.info("=" * 70)
        
        return changes_detected

if __name__ == "__main__":
    try:
        monitor = CertificationMonitor()
        monitor.scan_all_certifications()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise
