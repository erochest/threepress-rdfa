    $('#bw-shell-left').click(function() {
      if ($('span.bw-previous:first a').attr('href') != null) {
        document.location.href = $('span.bw-previous:first a').attr('href');
      }
    });
    /* Show directional clue when turning back */
    $('#bw-shell-left').hover(function() {
      $('#bw-left-arrow').fadeIn(2000);
    },
    function() {
      $('#bw-left-arrow').fadeOut('fast');
    }
    );

    /* Show directional clue when turning forward */
    $('#bw-shell-right').hover(function() {
      $('#bw-right-arrow').fadeIn(2000);
    },
    function() {
      $('#bw-right-arrow').fadeOut('fast');
    }
    );

    $('#bw-shell-right').click(function() {
      if ($('span.bw-next:first a').attr('href') != null) {
        document.location.href = $('span.bw-next:first a').attr('href');
      }
    });

       $(document).bind('keydown', function(e) {
           var code = (e.keyCode ? e.keyCode : e.which);
           if (code == 78 ) {  // 'n'
               if ($('span.bw-next:first a').attr('href') != null) {
                   document.location.href = $('span.bw-next:first a').attr('href');
               }
           }
           if (code == 80) {  // 'p'
               if ($('span.bw-previous:first a').attr('href') != null) {
                   document.location.href = $('span.bw-previous:first a').attr('href');
               }
           }
           if (code == 74) { // 'j'
               var current_top = $(window).scrollTop();
               var window_height = $(window).height();
               var para_height = $('#bw-main p').css('line-height');
               var scroll_to = current_top + window_height;
               if (para_height != null) {
                   para_height = parseInt(para_height.replace('px', ''));
                   scroll_to = scroll_to - (para_height * 2);
               }
               $('html, body').animate({ 
                       scrollTop: scroll_to
               }, 50);
           }
           if (code == 75 ) { // 'k'
               var current_top = $(window).scrollTop();
               var window_height = $(window).height();
               var para_height = $('#bw-main p').css('line-height');
               var scroll_to = Math.floor(current_top - window_height);
               if (para_height != null) {
                   para_height = parseInt(para_height.replace('px', ''));
                   scroll_to = scroll_to + (para_height * 2);
               }
               $('html, body').animate({ 
                       scrollTop: scroll_to
               }, 50);
           }
           });
