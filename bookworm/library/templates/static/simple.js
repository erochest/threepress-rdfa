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
            next();
        }
        if (code == 80) {  // 'p'
            previous();
        }
        if (code == 74) { // 'j'
            down(false);
        }
        if (code == 75 ) { // 'k'
            up();
        }
    });

function next() {
    if ($('span.bw-next:first a').attr('href') != null) {
        document.location.href = $('span.bw-next:first a').attr('href');
    }
}

function previous() {
    if ($('span.bw-previous:first a').attr('href') != null) {
        document.location.href = $('span.bw-previous:first a').attr('href');
    }
}

// Track the last place we went down so we can tell if we've hit the end
var last_down = '';
    
function down(go_next_at_bottom, override_height) {
    var speed = 50; // scrolling speed
    var current_top = $(window).scrollTop();
    var window_height = $(window).height();
    var document_height = $(document).height();
    if (override_height != null) {
       window_height = override_height; // for iphone
       speed = 0;
    }	
    var para_height = $('#bw-main p').css('line-height');
    var scroll_to = current_top + window_height;
    var test_bottom = scroll_to;
    if (para_height != null) {
        para_height = parseInt(para_height.replace('px', ''));
        scroll_to = scroll_to - (para_height * 2);
        test_bottom = scroll_to + para_height;
    }
    if (go_next_at_bottom && test_bottom >= document_height ) {
        return next();
    }
    $('html, body').animate({ 
            scrollTop: scroll_to
                }, speed);

    last_down = scroll_to;
}

function up() {
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
  
