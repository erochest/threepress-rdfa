jQuery(document).ready(function() {
        $("#bw-upload-box").hide();
        $('#bw-search-lang-selection').hide();

        $('#bw-upload-link').hover(function() {
                $("#bw-upload-box").slideDown('fast');
            },
            function() {} 
            );
        $('#bw-shell-table').hover(function() {
                $("#bw-upload-box").slideUp('fast');
            },
            function() {} );

        $('.bw-what-is-openid-link').click(function() {
                $("#bw-what-is-openid").fadeIn('normal');
            }
            );
        $('#bw-search-lang-change').click(function() {
                $("#bw-search-lang-selection").fadeIn('normal');
            }
            );
        $('#bw-search-lang-hide').click(function() {
                $("#bw-search-lang-selection").fadeOut('normal');
            }
            );

        $('#bw-librarything-images').cycle(
                { 
                    fx: 'fade', 
                    speed:  300, 
                    timeout: 0,
                    next:   '#bw-librarything-images', 
                    pause: 1
                 }
       );

            
    });

