 $(document).ready(function() {
    // Add animation to cards
    $('.card').hover(
        function() {
            $(this).addClass('animated pulse');
        },
        function() {
            $(this).removeClass('animated pulse');
        }
    );
    
    // Smooth scrolling for anchor links
    $('a[href^="#"]').on('click', function(event) {
        var target = $(this.getAttribute('href'));
        if (target.length) {
            event.preventDefault();
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 70
            }, 1000);
        }
    });
    
    // Add active class to current nav item
    var currentLocation = window.location.pathname;
    $('.navbar-nav .nav-link').each(function() {
        var link = $(this);
        if (link.attr('href') === currentLocation) {
            link.addClass('active');
        }
    });
    
    // Form validation
    $('form').on('submit', function() {
        var isValid = true;
        $(this).find('input[required], textarea[required]').each(function() {
            if ($(this).val() === '') {
                isValid = false;
                $(this).addClass('is-invalid');
            } else {
                $(this).removeClass('is-invalid');
            }
        });
        
        if (!isValid) {
            alert('Please fill in all required fields');
            return false;
        }
    });
    
    // File upload preview
    $('input[type="file"]').change(function() {
        var fileName = $(this).val().split('\\').pop();
        $(this).next('.custom-file-label').html(fileName);
    });
});