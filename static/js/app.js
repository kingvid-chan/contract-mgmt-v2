// Contract Management System - Client-side JS
// Bootstrap 5 handles most interactivity; this file contains custom enhancements.

(function () {
    'use strict';

    // Auto-dismiss flash alerts after 5 seconds
    document.addEventListener('DOMContentLoaded', function () {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function (alert) {
            setTimeout(function () {
                var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                if (bsAlert) {
                    try { bsAlert.close(); } catch (e) { /* already closed */ }
                }
            }, 5000);
        });
    });

    // File input: show filename on selection
    document.addEventListener('change', function (e) {
        if (e.target && e.target.type === 'file') {
            var fileName = e.target.files[0] ? e.target.files[0].name : '';
            var label = e.target.parentElement.querySelector('.file-name');
            if (label) {
                label.textContent = fileName;
            }
        }
    });

    // Confirm dangerous actions (handled by onsubmit inline, this is a fallback)
    var deleteForms = document.querySelectorAll('form[data-confirm]');
    deleteForms.forEach(function (form) {
        form.addEventListener('submit', function (e) {
            var message = form.getAttribute('data-confirm');
            if (message && !confirm(message)) {
                e.preventDefault();
            }
        });
    });
})();
