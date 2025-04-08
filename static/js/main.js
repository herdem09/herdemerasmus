document.addEventListener('DOMContentLoaded', function() {
    // Auto refresh data every 30 seconds
    setInterval(function() {
        // Only refresh if we're on the dashboard page
        if (document.querySelector('.dashboard')) {
            fetch('/api/data', {
                headers: {
                    'API-Key': 'gizli_anahtar123'
                }
            })
            .then(response => response.json())
            .then(data => {
                // Update temperature and light values
                document.getElementById('current-temp').textContent = data.sicaklik + '°C';
                document.getElementById('current-light').textContent = 'Işık: ' + data.isik;
                
                // Update status indicators
                updateStatusIndicators(data);
            })
            .catch(error => {
                console.error('Error fetching data:', error);
            });
        }
    }, 30000);
    
    // Function to update status indicators
    function updateStatusIndicators(data) {
        // Update status tiles
        updateStatusTile('isitici', data.isitici);
        updateStatusTile('vantilator', data.vantilator);
        updateStatusTile('pencere', data.pencere);
        updateStatusTile('kapi', data.kapi);
        updateStatusTile('perde', data.perde);
        updateStatusTile('ampul', data.ampul);
        
        // Update door status
        const doorStatus = document.querySelector('.door-status');
        if (doorStatus) {
            if (data.kapi) {
                doorStatus.classList.add('open');
                doorStatus.classList.remove('closed');
                doorStatus.querySelector('i').className = 'fas fa-door-open';
                doorStatus.querySelector('span').textContent = 'Kapı Açık';
            } else {
                doorStatus.classList.add('closed');
                doorStatus.classList.remove('open');
                doorStatus.querySelector('i').className = 'fas fa-door-closed';
                doorStatus.querySelector('span').textContent = 'Kapı Kapalı';
            }
        }
    }
    
    // Function to update a single status tile
    function updateStatusTile(name, active) {
        const tiles = document.querySelectorAll('.status-tile');
        for (const tile of tiles) {
            if (tile.querySelector('span').textContent.toLowerCase() === name) {
                if (active) {
                    tile.classList.add('active');
                } else {
                    tile.classList.remove('active');
                }
            }
        }
    }
    
    // Submit form when slider stops changing
    const sliders = document.querySelectorAll('input[type="range"]');
    for (const slider of sliders) {
        slider.addEventListener('change', function() {
            this.closest('form').submit();
        });
    }
});
